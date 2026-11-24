# Zeichnungsableitung – Recherche Normen und Praxis

Datum: 2026-11-16 · Status: Recherche, Grundlage für Brainstorming der Spec „Zeichnungsableitung“ in swki

## Kurzfassung

- **Belege:** Normausgaben sind gut belegt, Normtexte nicht gelesen. Einzelregeln stammen meist aus Lehr-, Wiki- und Herstellerseiten (Grad B) und taugen als Hausregel-Vorschlag, nicht als Normzitat.
- **Allgemeintoleranzen:** ISO 2768-2 (H/K/L) ist seit 04.02.2021 zurückgezogen und durch ISO 22081 ersetzt (DIN EN ISO 22081:2022-10, Werte in DIN 2769:2023-04). Ein undatiertes „ISO 2768-mK“ ist damit mehrdeutig. ISO 2768-1 gilt noch, eine neue ISO 2768 ohne Fasen/Radien ist in Veröffentlichung (unbestätigt).
- **Oberflächen:** ISO 1302 ist durch ISO 21920-1 ersetzt (DIN EN ISO 21920-1:2022-12). Standard ist jetzt die Max-Regel, die 16-%-Regel muss angegeben werden.
- **ISO 128 neu gegliedert:** Linien in 128-2 (DIN EN ISO 128-2:2023-06), Ansichten und Schnitte in 128-3 (DIN EN ISO 128-3:2024-06). 128-20/-24/-30/-34/-40/-44/-50 sind ersetzt.
- **Weitere Wechsel:**
  - ISO 5459:2024 (DIN EN ISO 5459:2025-12) ersetzt die Ausgabe 2011.
  - DIN 406-10/-11 sind 2020 zurückgezogen, es gilt DIN EN ISO 129-1:2022-02.
  - DIN 7167 ist zurückgezogen: Ohne Angabe gilt Unabhängigkeit (ISO 8015).
  - DIN 6771-2 ist zurückgezogen, für ISO 7573:2008 wurde keine DIN-Übernahme gefunden. Das Stücklistenlayout ist damit Firmenstandard.
- **Bemaßung:** Mit A belegt sind nur die Grundsätze: Bezug statt Kette, jedes Maß einmal, keine unnötig engen Toleranzen. ⌴/⌵/↧, „C2“, die Schreibweise nach ISO 15786 und Maßlinienabstände sind Hausregel-Entscheidungen.
- **swki:** `bezug` passt auf Bezugs- bzw. Symmetriebemaßung. Für Toleranz, Passung, Oberfläche, Form und Lage, Bezüge, Funktionsflächen, Halbzeug und Zeichnungsnummer fehlen Spec-Felder.
- **API 2025:**
  - Fast alles geht ohne Dialog, aber stark auswahlgetrieben. Der deterministischste Weg ist die Übernahme der „für Zeichnung markierten“ Modellmaße.
  - `AddHoleCallout2` braucht einen Dialog. Für ISO 13715 wurde keine API gefunden, DimXpert fehlt im Index.
  - SP-Abhängigkeiten: `GetFirstDisplayDimension6` ab SP1, `GetAnnotationsByType` ab SP2.

## Belegskala und Quellenlage

| Grad | Bedeutung |
|---|---|
| **A** | ≥ 2 unabhängige Quellen stimmen überein (mindestens eine davon gelesen) |
| **B** | eine Quelle, oder die Aussage liegt nur als Suchauszug (Snippet) einer nicht geöffneten Seite oder PDF vor (Suchauszug höchstens B) |
| **C** | unbelegt bzw. Hintergrundwissen der Rechercheure. In den Tabellen als „C, unbelegt“ markiert, nicht verwenden ohne Gegenprüfung |

**Quellenlage:**
- **Normvolltexte wurden nicht gelesen.** Sie sind kostenpflichtig. iso.org und die ISO-OBP-Vorschau lieferten HTTP 403 bzw. verlangen die Zustimmung zu Nutzungsbedingungen, die ohne OK des Nutzers nicht erteilt wurde. iTeh- und SIS-Katalogseiten laden ihren Inhalt per JavaScript.
- Die Belege sind überwiegend sekundär: Hochschul- und Lehrseiten, Wikipedia, Herstellerseiten und Verlagsmetadaten (DIN Media). Wörtliche Normsätze (z. B. ISO 6433, ISO 7573) stammen nur aus Suchauszügen der Vorschau-PDFs.
- Volltextkopien (Studocu, pdfcoffee, kupdf, Scribd, model-r.ru, idoc.pub-Scan Hoischen) wurden **nicht** als Beleg verwendet.
- Herabstufungen: Wo eine Notiz A vergab, die Aussage aber nur auf Suchauszügen ruht, steht hier B mit dem Vermerk „Notiz: A“.
- Bei einigen A-Zeilen ist nur eine Quelle gelesen, die zweite liegt als Suchauszug vor. Diese Grade sind aus den Notizen übernommen, aber schwächer als ein A aus zwei gelesenen Quellen. Betroffen sind:
  - Rückzug von DIN 7167 und DIN 406
  - Ablösung der ISO-128-Altteile durch ISO 128-3
  - ISO 21920 ersetzt ISO 1302 (BSI nur Suchauszug)
  - „unterstrichen = nicht maßstäblich“
  - SR = Kugelradius
  - Grundzuordnung der Passungen
  - Freistich nur mit Normbezeichnung
  - Biegeradius R ≥ s
  - Nennmaße < 0,5 mm
  - POS-01, POS-03, POS-05, POS-09, POS-10
- In der Spalte „prüfbar“ steht teils die erzeugende Methode als Hinweis auf das zu prüfende Objekt (z. B. `SetDisplayMode4`, `SetLabel2`, `InsertBreak3`, `AlignDimensions`). Die passenden Lese-Methoden wurden nicht in jedem Fall nachgeschlagen.
- Wo verschiedene Notizen dieselbe Regel verschieden bewerten, stehen beide Grade mit Notiz-Nummer da (01 Blatt und Darstellung, 02 Bemaßung, Gewinde, Kanten, 03 Toleranzen und Oberflächen, 04 Baugruppe, 05 fertigungsgerecht, 06 API). Zwei B aus verschiedenen Notizen ergeben kein A.

**Folge für die Nutzung:**
- A-Regeln können als Prüfregel umgesetzt werden.
- B-Regeln als konfigurierbare Hausregel mit Quellenvermerk.
- C-Regeln nur nach Abgleich mit dem Normtext oder ausdrücklicher Entscheidung des Nutzers.
- Normausgaben gehören als Daten in eine Tabelle, nicht in den Code (Repo-Regel „nie ein Jahr fest in Code schreiben“).

**Kapitel 10 (API) hat eine eigene Skala.**
- Primärquelle ist der Offline-Index der SolidWorks-2025-API-Hilfe im Repo (`swki api methode/enum/suche`, HTML-Kopie offline gelesen). Er gilt als *eine* Quelle, ist aber Primärdokumentation; die Einschränkung „kein Volltext gelesen“ gilt dort nicht.
- A = Index plus ein zweites gelesenes Dokument (codestack.net-Artikel oder eigenständiges Hilfe-Beispiel).
- B = Index allein.
- C = Hintergrundwissen, Foren oder Suchauszug, z. B. UI-Hilfe von help.solidworks.com, das ohne JavaScript nicht lesbar war.
- Das Feld `seit` im Index trägt nur das Jahr, nicht das Service Pack.

**Spalte „prüfbar durch swki“.** Sie sagt, ob swki eine Regel automatisch prüfen könnte und aus welcher Datenquelle:
- **S** = Spec (YAML nach `schema/teil.schema.json` / `baugruppe.schema.json`)
- **M** = gebautes Modell (wie heute `swki pruefen`)
- **Z** = Zeichnung über die API zurückgelesen
- **V** = Vorlage (.drwdot/Blattformat/.sldstd, einmal prüfen)
- **P** = Prüfer-Agent mit Bild bzw. PDF der Zeichnung

swki hat heute **kein Zeichnungsmodul**. Jedes „Z“ heißt deshalb „bräuchte Rücklesen nach Kap. 10“.

Die Spec kennt heute:
- `material` (Text) und `eigenschaften` (freie Text-Map)
- `parameter`, Features mit `bezug`, `fase` an Bohrungen, `normbohrung` (Größe, Gewindetiefe), `muster_*` und `spiegeln`
- `pruefung` (`masse_pruefen.tol` ist eine Prüftoleranz, keine Zeichnungstoleranz)
- Baugruppen: `komponenten` mit `quelle` `teil`/`normteil`/`kaufteil`, `verknuepfungen` und `bewegungen`

Es gibt **keine** Felder für Maßtoleranz, Passung, Oberfläche, Form und Lage, Bezugssystem, Funktionsfläche, Halbzeug, Kantenzustand und Zeichnungsnummer. Solche Regeln stehen als „bräuchte …“.

## 1. Normenstand

| Norm (Thema) | Gültige Ausgabe (DE) | Ersetzt / Status | Beleg | Quelle |
|---|---|---|---|---|
| ISO 5457 (Formate, Rahmen) | DIN EN ISO 5457:2017-10 (= EN ISO 5457:1999 + A1:2010) | ersetzt DIN EN ISO 5457:1999-07; Korrektur 2010-11 in 4.4 „linken“ → „rechten Rand“ (Inhalt unklar) | B | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-5457/278410251) |
| ISO 7200 (Schriftfeld) | DIN EN ISO 7200:2004-05 (ISO 7200:2004) | ersetzt DIN EN ISO 7200-1/-2:1999-04; in DE Nachfolger von DIN 6771-1 (A) | B (Ausgabe, Suchauszug) | [din.de](https://www.din.de/en/wdc-beuth:din21:69093619); [Wikipedia DE Schriftfeld](https://de.wikipedia.org/wiki/Schriftfeld); [Wikipedia EN ISO 7200](https://en.wikipedia.org/wiki/ISO_7200) |
| ISO 5455 (Maßstäbe) | DIN ISO 5455:1979-12; EN ISO 5455:1995 auf EU-Ebene | ob in DE eine DIN-EN-ISO-Fassung gilt, ungeklärt | B (Suchauszug) | [DIN Media](https://www.dinmedia.de/en/standard/din-iso-5455/790721) |
| ISO 3098-1 (Schrift) | DIN EN ISO 3098-1:2015-06 | ersetzt DIN EN ISO 3098-0:1998-04 | B (Suchauszug) | [DIN Media](https://www.dinmedia.de/en/standard/din-en-iso-3098-1/232192579) |
| ISO 128-1 (Grundregeln) | ISO 128-1:2020 | DE-Ausgabe nicht geprüft | B | [Wikipedia EN ISO 128](https://en.wikipedia.org/wiki/ISO_128) |
| ISO 128-2 (Linien) | DIN EN ISO 128-2:2023-06 (= ISO 128-2:2022) | ersetzt DIN EN ISO 128-2:2022-02; ISO 128-2:2022 ersetzt 128-2:2020; ersetzt ISO 128-20, -21, -22, -23, -24, -25; DIN ISO 128-24:1999-12 zurückgezogen. Maschinenbau jetzt in Anhängen B–G | B | [DIN Media 128-2](https://www.dinmedia.de/de/norm/din-en-iso-128-2/361281642); [DIN Media 128-24](https://www.dinmedia.de/de/norm/din-iso-128-24/23592503); [SIS](https://www.sis.se/en/produkter/standardization/technical-drawings/general/iso-128-22020/); [Wikipedia EN](https://en.wikipedia.org/wiki/ISO_128) |
| ISO 128-3 (Ansichten, Schnitte, Schraffur) | DIN EN ISO 128-3:2024-06 (= ISO 128-3:2022, 63 S.) | ersetzt DIN EN ISO 128-3:2022-02, diese ersetzte DIN ISO 128-40/-50:2002-05; ISO 128-3 ersetzt ISO 128-30, -33, -34, -40, -44, -50 | A für Ablösung der Altteile; B für DE-Ausgabe 2024-06 (Suchauszug) | [DIN Media 128-3](https://www.dinmedia.de/en/standard/din-en-iso-128-3/359489181); [Wikipedia EN](https://en.wikipedia.org/wiki/ISO_128); [DIN Media 128-50](https://www.dinmedia.de/en/standard/din-iso-128-50/46948186) |
| ISO/TS 128-71 (vereinfachte Darstellung Maschinenbau) | ISO/TS 128-71:2010 | aktuell | B | [Wikipedia EN](https://en.wikipedia.org/wiki/ISO_128) |
| ISO 128-22 (Hinweislinien) | ISO 128-22:1999 | laut Wikipedia EN durch ISO 128-2 ersetzt (Notiz 01); Notiz 04 nutzt sie noch für POS-05, Status dort ungeprüft | B | [Wikipedia EN](https://en.wikipedia.org/wiki/ISO_128) |
| ISO 5456-2 (Projektion) | ISO 5456-2:1996 | DE-Status nicht geprüft; ISO 128-3 verweist für das Symbol darauf (Suchauszug) | B | [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) |
| ISO 129-1 (Bemaßung) | DIN EN ISO 129-1:2022-02 (= ISO 129-1:2018 + Amd 1:2020), 83 S. | ersetzt DIN EN ISO 129-1:2020-02; ISO 129-1:2018 zuletzt 2023 bestätigt | A (ISO-Status), B (DE-Ausgabe) | [ISO 64007](https://www.iso.org/standard/64007.html); [SIS A1:2021](https://www.sis.se/produkter/terminologi-och-dokumentation/dokumentation-av-tekniska-produkter/ss-en-iso-129-12019a12021/); [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-129-1/333197796) |
| DIN 406-10/-11 (alte Maßeintragung) | zurückgezogen (Februar 2020) | DIN EN ISO 129-1:2020-02 ersetzte DIN 406-10, -11 und 406-11 Beiblatt 1. Notiz 05 fand den Ersatz für 406-11 nicht, Notiz 02 belegt ihn | Rückzug A; Ersatzvermerk B (nur Suchauszug DIN Media; Notiz 02: A) | [Wikipedia DE Bemaßung](https://de.wikipedia.org/wiki/Bema%C3%9Fung); [DIN Media 129-1:2020](https://www.dinmedia.de/de/norm/din-en-iso-129-1/314070706); [DIN Media 406-10](https://6sku3uaup9f9.din.de/en/standard/din-406-10/1990706) |
| ISO 15786 (Bohrungen vereinfacht) | ISO 15786:2008 (2024 bestätigt); DIN ISO 15786:2014-12 | aktuell | A | [ISO 42099](https://www.iso.org/standard/42099.html); [din.de](https://www.din.de/en/wdc-beuth:din21:223068266) |
| ISO 13715 (Kanten) | DIN EN ISO 13715:2020-01 (= EN ISO 13715:2019 = ISO 13715:2017) | ersetzt DIN ISO 13715:2018-09, keine technischen Änderungen; eine „ISO 13715:2019“ gibt es nicht | A | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-13715/314070606); [BSI](https://knowledge.bsigroup.com/products/technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning); [EVS](https://www.evs.ee/en/evs-en-iso-13715-2019) |
| ISO 6410-1/-3 (Gewinde) | ISO 6410-1:1993 (2024 bestätigt; EN ISO 6410-1:1996); DIN EN ISO 6410-3:2021-12 | -3 ersetzt DIN ISO 6410-3:1993-12; Teil 2 nicht geprüft | A (Teil 1), B (Teil 3, Suchauszug) | [ISO 12750](https://committee.iso.org/standard/12750.html); [SAI Global](https://infostore.saiglobal.com/en-us/standards/iso-6410-1-1993-591686_saig_iso_iso_1355305/); [DIN Media 6410](https://www.dinmedia.de/en/standard/din-iso-6410/2584244) |
| ISO 2768-1 (Allgemeintoleranzen Längen/Winkel) | DIN ISO 2768-1:1991-06 (= ISO 2768-1:1989) | din.de „AKTUELL“; ISO-Stufe 90.92 „to be revised“; neue einteilige ISO 2768 (Stufe 60.00 „under publication“, FDIS 23.03.2026) soll sie ersetzen, Veröffentlichung unbestätigt | B | [din.de](https://www.din.de/de/wdc-beuth:din21:1718351); [Wevolver](https://www.wevolver.com/article/iso-2768-general-tolerances-tables-classes-current-status); [iteh FDIS](https://standards.iteh.ai/catalog/standards/iso/0c8e062e-4aa9-48d5-a245-94ade8dfd018/iso-fdis-2768) |
| E DIN EN ISO 2768 | Entwurf 2025-09 (ISO/DIS 2768:2025) | vier Klassen, nur Größenmaße; Fasen/Radien gestrichen | B | [DIN Media Entwurf](https://www.dinmedia.de/de/norm-entwurf/din-en-iso-2768/394170392) |
| ISO 2768-2 (H/K/L) | **zurückgezogen 04.02.2021** | Nachfolger ISO 22081:2021; DIN ISO 2768-2:1991-04 zurückgezogen, ersetzt durch DIN EN ISO 22081:2022-10 (B) | A | [genorma](https://genorma.com/en/standards/iso-2768-2-1989); [Wevolver](https://www.wevolver.com/article/iso-2768-general-tolerances-tables-classes-current-status); [Austrian Standards](https://austrian-standards.at/de/shop/iso-2768-2-1989-1989-11-02~p1222103) |
| ISO 22081 (allgemeine GPS-Spezifikation) | DIN EN ISO 22081:2022-10 (ISO 22081:2021) | aktuell; laut DIN-Einführung „fälschlich“ als Ersatz von 2768-2 gekennzeichnet (Suchauszug) | B | [din.de](https://www.din.de/en/wdc-beuth:din21:356826589) |
| DIN 2769 (Zahlenwerte zu ISO 22081) | DIN 2769:2023-04 | ersetzt 2021-12; Entwurf DIN 2769:2026-09 (Kopplung an 3D-Modell) | B | [DIN Media](https://www.dinmedia.de/de/norm/din-2769/364625893); [Entwurf](https://www.dinmedia.de/de/norm-entwurf/din-2769/404718083) |
| ISO 8015 (Tolerierungsgrundsatz) | DIN EN ISO 8015:2011 | aktueller Status nicht bestätigt | C (Status) | – |
| DIN 7167 (Hülle ohne Eintrag) | **zurückgezogen April 2011** | stattdessen DIN EN ISO 14405-1 | A | [Wikipedia DE Allgemeintoleranz](https://de.wikipedia.org/wiki/Allgemeintoleranz); [DIN Media](https://www.dinmedia.de/de/norm/din-7167/1333468) |
| ISO 14405-1 (Größenmaße) | DIN EN ISO 14405-1:2017-07 | ersetzt 2011-04 | B (Suchauszug) | [DIN Media](https://www.dinmedia.de/en/standard/din-en-iso-14405-1/132686225) |
| ISO 286-1/-2 (Passungen) | ISO 286-1/-2:2010; DE vermutlich 2019-09 | DE-Ausgabe nicht bestätigt | B/C | [TU Darmstadt](https://www.iim.maschinenbau.tu-darmstadt.de/CAD-Tutorial/CAD-Norminfo/3_important_standards_and_data_sheets/3_tolerances_and_fits/1_selection_and_calculation_of_fits/index.en.html) |
| ISO 1101 (Form und Lage) | ISO 1101:2017 (4. Ausg.); DIN EN ISO 1101:2017-09 | 3. Ausgabe 2012 zurückgezogen, keine Änderung nach 2017 gefunden | B (nur Suchauszüge; Notiz: A) | [SNV](https://insights.snv.ch/en/page/how-to-comply-with-iso-11012017-a-comprehensive-gu-en); [standards.ie](https://shop.standards.ie/en-ie/standards/din-en-iso-1101-2017-09-409769_saig_din_din_925799) |
| ISO 2692 (Maximum-Material) | ISO 2692:2021 (4. Ausg.) | ersetzt 2014; neu: virtuelle Größe direkt, Symbole SZ/CZ | B | [EVS](https://www.evs.ee/en/evs-en-iso-2692-2021) |
| ISO 5459 (Bezüge) | **ISO 5459:2024-10; DIN EN ISO 5459:2025-12** (154 S.) | ersetzt ISO 5459:2011 bzw. DIN EN ISO 5459:2013-05; Inhalt der Änderungen nicht recherchiert | B (nur Suchauszüge; Notiz: A) | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-5459/385519058); [din.de ISO 5459:2024](https://6sku3uaup9f9.din.de/en/standard/iso-5459/385088699) |
| ISO 21920-1 (Oberflächenangabe) | **DIN EN ISO 21920-1:2022-12** (ISO 21920-1:2021) | ersetzt DIN EN ISO 1302:2002-06 + Ber. 1:2008-08; -2 ersetzt ISO 4287, 13565-2/-3; -3 ersetzt ISO 4288; DIN EN ISO 4287 am 25.01.2022 zurückgezogen | A | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-21920-1/344762052); [Quality Magazine](https://www.qualitymag.com/articles/98952-evolving-roughness-standards-understanding-and-implementing-iso-21920); [Wikipedia DE Rauheit](https://de.wikipedia.org/wiki/Rauheit) |
| ISO 6433 (Positionsnummern) | DIN EN ISO 6433:2012-12 | ersetzt DIN ISO 6433:1982-09; ISO 6433:2012 ersetzt 1981 (A); BSI: „Current, Under Review“ | B (DE), A (ISO) | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-6433/149924295); [standards.ie](https://shop.standards.ie/en-ie/standards/iso-6433-2012-581291_saig_iso_iso_1330605); [BSI](https://knowledge.bsigroup.com/products/technical-product-documentation-part-references-part-references) |
| ISO 7573 (Stücklisten) | ISO 7573:2008 (bestätigt Dez. 2023) | ersetzt ISO 7573:1983; keine DIN-EN-Übernahme gefunden | A (gültig), B (Datum) | [genorma](https://genorma.com/en/standards/iso-7573-2008); [iTeh 1983](https://standards.iteh.ai/catalog/standards/iso/c486fd85-38de-460c-907c-b2acf8a13f15/iso-7573-1983) |
| DIN 6771-2 (Stücklistenvordruck) | **zurückgezogen** | Rückzug 2007-10 nur B; Ausgabe 1975-09 vs. 1987-02 widersprüchlich | A (Rückzug) | [Wikipedia DE Stückliste](https://de.wikipedia.org/wiki/St%C3%BCckliste); [DIN NATG](https://www.din.de/en/getting-involved/standards-committees/natg/publications/wdc-beuth:din21:1433478); [SAI Global](https://infostore.saiglobal.com/en-us/standards/iso-7573-2008-584540_saig_iso_iso_1338544/) |
| DIN 199-1 (Begriffe TPD) | 2024-06? | 2002-03 zurückgezogen | C (nur Suchauszug, nicht verifiziert) | [DIN Media](https://www.dinmedia.de/en/standard/din-199-1/46493205) |
| DIN 509 (Freistiche) | DIN 509:2022-12 | ersetzt 2006-12 | B | [DIN Media](https://www.dinmedia.de/de/norm/din-509/359215693) |
| ISO 6411 (Zentrierbohrungen) | DIN ISO 6411:1997-11 | ersetzt DIN 332-10:1983-12 | B | [DIN Media](https://6sku3uaup9f9.din.de/en/standard/din-iso-6411/3044538) |
| DIN 36-2 (Bruchlinien) | zurückgezogen | – | B (Suchauszug) | [DIN Media](https://www.dinmedia.de/en/draft-standard/din-36-2/250206899) |

**Widersprüche:**
- Wikipedia EN führt ISO 128-2:2020 als aktuell, SIS/EVS melden sie als durch 2022 ersetzt. Wikipedia ist veraltet.
- ISO 128-24: Wikipedia nennt die Ausgabe 2014, DIN Media die zurückgezogene DIN ISO 128-24:1999-12. Beide Ausgaben existierten.
- ISO 128-3: Notiz 04 ließ 2020 vs. 2022 offen. Notiz 01 klärt per DIN-Media-Suchauszug: DIN EN ISO 128-3:2024-06 = ISO 128-3:2022. Welche ISO-Ausgabe die zurückgezogene DIN EN ISO 128-3:2022-02 übernahm, bleibt C.
- DIN 2769 heißt bei DIN Media „Nachfolger“ der DIN-ISO-2768-Reihe, din.de führt DIN ISO 2768-1:1991-06 aber weiter als „AKTUELL“.
- Lehrseiten (ingenieurkurse, lehrerfreund, Wikibooks, Wikipedia DE) zitieren zurückgezogene Teile (ISO 128-20/-24/-30, DIN EN ISO 3098-0, DIN 6, DIN 15, DIN 201, DIN 6771-2). Die Regeln sind meist weitergeführt, die Verweise aber veraltet.

**Status nicht geprüft:**
- DIN ISO 5456-2 (DE)
- DIN EN ISO 128-1 (DE)
- DIN ISO 5455:1979-12 gegenüber EN ISO 5455:1995
- laufende Revision ISO 7200
- ISO 8015:2011
- DE-Ausgabe ISO 286-1/-2
- ISO 6410-2:1993
- Veröffentlichung der neuen ISO 2768 und ihre DIN-EN-Übernahme
- Revision ISO 6433 (BSI „under review“)
- Gültigkeit ISO 128-22:1999 als eigene Norm

## 2. Blatt, Rahmen, Schriftfeld, Maßstäbe, Schrift

### Blatt und Rahmen (ISO 5457)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Formate (ISO 216) | A4 210 × 297, A3 297 × 420, A2 420 × 594, A1 594 × 841, A0 841 × 1189 mm | [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) | B | ja – Z (`ISheet.GetProperties2`), V |
| A4-Lage | seit A1:2010 hoch und quer zulässig | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-5457/278410251) | B | ja – Z |
| Ränder | links 20 mm einschl. Rahmen, übrige 10 mm | [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/); [Wikipedia DE Schriftfeld](https://de.wikipedia.org/wiki/Schriftfeld) | A | ja – V (einmal je Blattformat) |
| Rahmenlinie | Volllinie 0,7 mm; außerhalb nichts zeichnen | checkedcalc | B | ja – V; „nichts außerhalb“: ja – Z (`IView.GetOutline`, Annotationslagen) |
| Zentriermarken | vier, je Seitenmitte | checkedcalc | B | ja – V |
| Feldeinteilung | 50-mm-Felder ab Zentriermarken; Buchstaben (ohne I, O) oben → unten, Ziffern links → rechts; A3 8 × 6, A4 6 × 4 | checkedcalc | B | ja – V |
| Zentriermarke als 0,7-mm-Linie bis 10 mm über Rahmen; Feldlinien 0,35 mm; A0 24 × 16, A1 16 × 12, A2 12 × 8; A4 Felder nur oben/rechts; Schneidemarken 10 × 5 mm | – | – | C, unbelegt (nur aus nicht verwendbaren Volltextkopien) | – |

**Widersprüche:** Die Fassung 1999 zeigt A0–A3 quer und A4 hoch ([checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/)). Wikipedia DE nennt für größere Formate „nur Querformat“. Seit A1:2010 ist A4 in beiden Lagen zulässig (DIN Media).

### Schriftfeld (ISO 7200)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Pflichtfelder (8) | gesetzl. Eigentümer, Sachnummer, Ausgabedatum, Abschnitts-/Blattnummer, Titel, Freigebender, Ersteller, Dokumentart | [Wikipedia DE Schriftfeld](https://de.wikipedia.org/wiki/Schriftfeld); [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) | A | ja – Z (`ICustomPropertyManager.Get6`, `INote.GetText`); S nur teilweise (`eigenschaften` frei, keine Pflichtschlüssel) |
| übrige Felder | optional (z. B. Änderungsindex, Blattanzahl); Firmen machen sie oft zur Pflicht | Wikipedia DE; checkedcalc | A | Hausregel – Z |
| Breite | 180 mm (= 210 − 20 − 10); Regel (Wikipedia DE) oder Beispielmaß (checkedcalc) | Wikipedia DE; checkedcalc | B je Lesart | ja – V (≤ 180 mm als Prüfregel) |
| Lage | rechte untere Ecke; bei A4 hoch unten; bei Faltung (DIN 824) lesbar | Wikipedia DE | B | ja – V |
| Aufteilung | Zeilen und Spaltenbreiten frei, Zeichenzahl nur empfohlen | Wikipedia DE | B | – |
| Revisionsindex | optionales Feld, 2 Zeichen; Revisionen A–Z, dann AA, AB …; „I und O meiden“ nur Blog | [draftsperson.net](https://blog.draftsperson.net/drawing-sheet-layout-metric/); IS 11665:2009 (Suchauszug) | B (Notiz 04); Notiz 01: C | Hausregel – Z |
| empfohlene Zeichenzahlen | Sachnummer 16, Änderungsindex 2, Ausgabedatum 10 (ISO 8601 JJJJ-MM-TT), Titel 25 | – | C, unbelegt | – |
| Maßstab, Projektionssymbol, Allgemeintoleranz, Oberfläche | keine ISO-7200-Felder, stehen in Kästen neben dem Schriftfeld | checkedcalc | B | ja – Z (Prüfung „im oder unmittelbar neben dem Schriftfeld“) |

**Widersprüche:** Laut [ingenieurkurse](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/massstaebe-nach-din-iso-5455.html) ist der Maßstab „im Schriftfeld … zwingend einzutragen“. Laut [Wikipedia DE TZ](https://de.wikipedia.org/wiki/Technisches_Zeichnen) sitzt das Projektionssymbol im Schriftfeld. checkedcalc ordnet beides neben das Schriftfeld. Wikipedia DE ist beim Ausgabemonat von ISO 7200 in sich widersprüchlich (Februar vs. Mai 2004; ISO 2004-02, DIN 2004-05).

### Maßstäbe (ISO 5455)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Vorzugsmaßstäbe | 50:1, 20:1, 10:1, 5:1, 2:1; 1:1; 1:2, 1:5, 1:10, 1:20 … (Folge 1-2-5) | [ingenieurkurse](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/massstaebe-nach-din-iso-5455.html); [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) | A | ja – Z (`IView.ScaleRatio`, `ISheet.GetProperties2`) |
| weitere Verkleinerungen | bis 1:10000; nur die genannten Maßstäbe verwenden | ingenieurkurse | B | ja – Z |
| Angabe | Hauptmaßstab im Schriftfeld(-bereich), abweichende bei Ansicht, Einzelheit, Schnitt | ingenieurkurse; checkedcalc | A | ja – Z (Ansicht mit `UseSheetScale` = false braucht Beschriftung) |
| Schreibweise „1:2“ / „M 1:2“ / „Maßstab 1:2“; Zwischenmaßstäbe 1:2,5, 1:4 in Ausnahmen | – | – | C, unbelegt | – |

### Schrift (ISO 3098-1)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Nenngrößen h | 1,8 / 2,5 / 3,5 / 5 / 7 / 10 / 14 / 20 mm (Stufung √2) | [Wikibooks](https://de.wikibooks.org/wiki/Technisches_Zeichnen/_Linien_und_Beschriftung); [wiechmann-at.de](http://www.wiechmann-at.de/MBStudium/TechnischesZeichnen/TZSchriften.html) | A | ja – Z (`IDisplayData.GetTextHeightAtIndex`), V |
| Schriftform | B: d = h/10 (bevorzugt), A: d = h/14 (Platzmangel); Form B 2,5/3,5/5/7 ↔ Linienbreite 0,25/0,35/0,5/0,7 | wiechmann-at.de; Vieweg-Leseprobe (Suchauszug) | B | teilweise – V (in CAD nur Höhe und Neigung prüfbar) |
| Neigung | senkrecht oder 15° nach rechts | Wikibooks; wiechmann-at.de | A | ja – V |
| Abstände | zwischen Linien und Buchstaben ≥ 2 × Linienbreite | wiechmann-at.de | B | – |
| Mindesthöhe | h ≥ 2,5 mm, bei Groß- und Kleinschreibung ≥ 3,5 mm | „Bautechnik Technisches Zeichnen“ (Suchauszug) | B | ja – Z |
| Maßzahl ≥ 3,5 mm (Fertigungszeichnung, TUM-Hausregel) | – | [TUM Zeichnungserstellung](https://www.epe.ed.tum.de/fileadmin/w00bzo/ewt/Werkstatt/Zeichnungserstellung.pdf) (Suchauszug) | B | ja – Z |
| Maßzahl 3,5 mm (A4–A2) bzw. 5 mm (A1/A0); Titel/Sachnummer 5 oder 7 mm | – | – | C, unbelegt | – |

**Widersprüche:** Die Wikibooks-Tabelle gibt für beide Schriftformen d = h/14 an. Ihre eigenen Beispiele für Form B entsprechen h/10. Die Tabelle ist offenbar falsch übertragen, die Form-B-Werte dort sind unbrauchbar.

## 3. Linien und Darstellung

### Linienarten und -breiten (ISO 128-2)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Definition Linie | Länge > 0,5 × Linienbreite | [ingenieurkurse Linien](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/linien-linienarten-und-deren-anwendung.html); [Wikibooks](https://de.wikibooks.org/wiki/Technisches_Zeichnen/_Linien_und_Beschriftung) | A | – |
| Grundarten | 01 Voll-, 02 Strich-, 03 Strich-Abstands-, 04 Strich-Punkt- (lang), 05 Strich-Zweipunkt-, 06 Strich-Dreipunkt-, 07 Punktlinie …; Varianten von 01: Wellen-, Zickzack-, Freihandlinie | ingenieurkurse (zitiert ISO 128-20) | B | – |
| Breitenverhältnis | breit : schmal = 2 : 1; Liniengruppe = Breite der breiten Linie | ingenieurkurse; [Wikipedia DE TZ](https://de.wikipedia.org/wiki/Technisches_Zeichnen); [lehrerfreund](https://www.lehrerfreund.de/technik/1s/technisches-zeichnen-stricharten-strichstaerken/4482) | A | ja – V (Dokumenteigenschaften Linienstärken) |
| Gruppen 0,5 und 0,7 | 0,5/0,25 und 0,7/0,35 mm | Wikipedia DE TZ; lehrerfreund | A | ja – V |
| Gruppen 0,35 und 1 | 0,35/0,18 und 1/0,5 mm | ingenieurkurse | B | ja – V |
| Gruppe nach Format | 0,5 für A2 und kleiner, 0,7 für A1/A0; dritte mittlere Breite (0,35 bei Gruppe 0,5) für Schrift, Symbole, verdeckte Kanten möglich | Wikipedia DE TZ | B | ja – V/Z (Format aus `GetProperties2`) |
| eine Gruppe je Zeichnung | alle Linien, Maße, Symbole aus derselben Gruppe | lehrerfreund; ingenieurkurse | A | ja – V |
| breite Volllinie | sichtbare Kanten und Umrisse | lehrerfreund; Wikipedia DE TZ | A | teilweise – V (Linienstil je Kantentyp in Dokumenteigenschaften; je Kante nicht recherchiert) |
| breite Volllinie, weitere Fälle | Gewindespitzen, Grenze nutzbare Gewindelänge | lehrerfreund | B | teilweise – V |
| schmale Volllinie | Maß-, Maßhilfslinien, Schraffur | lehrerfreund; Wikipedia DE TZ | A | teilweise – V |
| schmale Volllinie, weitere Fälle | Lichtkanten, Hinweis- und Bezugslinien, kurze Mittellinien, Gewindegrund | lehrerfreund | B | teilweise – V |
| schmale Strichlinie | verdeckte Kanten | lehrerfreund; Wikipedia DE TZ | A | ja – Z (`IView.SetDisplayMode4`, Modus HIDDEN/HIDDEN_GREYED) |
| schmale Strichpunktlinie | Mittel-, Symmetrielinien, Teilkreise | lehrerfreund; Wikipedia DE TZ | A | teilweise – Z (Mittellinien/Mittelpunktmarken vorhanden: `GetAnnotations`, Typ CenterLine/CenterMarkSym) |
| breite Strichpunktlinie | Schnittebenen, begrenzte Bereiche (z. B. Wärmebehandlung) | lehrerfreund | B | – |
| schmale Strich-Zweipunktlinie | Umrisse angrenzender Teile, Endlagen beweglicher Teile, Schwerpunktlinien | lehrerfreund | B | – |
| Freihand-/Zickzacklinie schmal | Begrenzung abgebrochener Ansichten und Teilschnitte | lehrerfreund; Wikipedia DE TZ; [mechatronik-automatisierung.com](https://mechatronik-automatisierung.com/technische-doku/zeichnung-lesen/schnitte/) | A | ja – Z (`swBreakLineStyle_e` ZigZag/SmallZigZag) |
| Kreuzungsregel | Strich- und Strichpunktlinien treffen sich in Strichen, nicht in Lücken | lehrerfreund | B | P |
| Mittellinienüberstand ca. 2–5 mm; alte Bezeichnungen 01.1/01.2/02.1/04.1/04.2/05.1; Strich-/Lückenlängen (12d/3d, 24d/3d/0,5d); Mindestabstand paralleler Linien ≥ 0,7 mm | – | – | C, unbelegt | – |

**Widersprüche:**
- ingenieurkurse nennt für Gruppe 0,7 die schmale Linie mit 0,3 mm und bricht damit das eigene 2:1-Verhältnis. Lehrerfreund und Wikipedia DE nennen 0,35 mm, das ist konsistent.
- Schnittverlauf: Lehrerfreund nennt eine breite Strichpunktlinie. Laut mechatronik-automatisierung.com (ÖNORM EN ISO 128-3) ist er eine Strichpunktlinie, nur an Enden und Richtungswechseln breit.
- Ob die Gruppenwerte im Maschinenbau-Anhang von ISO 128-2:2022 unverändert stehen, ist nicht eingesehen.

### Projektionsmethode und Ansichten (ISO 5456-2, ISO 128-3)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Projektionsmethode 1 (europäisch) in DE; Methode 3 = amerikanisch | – | [Wikipedia DE TZ](https://de.wikipedia.org/wiki/Technisches_Zeichnen); Suchauszüge Frankfurt UAS, Onshape | A | ja – Z (`ISheet.GetProperties2` firstAngle; `SetupSheet6` FirstAngle) |
| Projektionssymbol | im Schriftfeld (Wikipedia DE) bzw. neben dem Schriftfeld (checkedcalc, ISO 5456-2:1996) | Wikipedia DE TZ; [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) | B (Widerspruch) | ja – V |
| Hauptansichten | Vorderansicht, Seitenansicht von links, Draufsicht; weitere nur, wenn nötig | Wikipedia DE TZ | B | P |
| Wahl der Vorderansicht | aussagefähigste Ansicht (Form, Größe); alternativ Fertigungs- oder Gebrauchslage | Uni Wuppertal CAD-m1 (Suchauszug) | B | teilweise – S/M (Drehteil aus `rotation`, Hauptbearbeitungsrichtung aus Skizzenebenen), sonst P |
| isometrische Ansichten nicht bemaßen | nur orthogonale Ansichten bemaßen | [industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/engineering-drawing-dimensioning-best-practices-guide) (Suchauszug) | B | ja – Z (Ansichtstyp + `GetDisplayDimensions`) |
| Anordnung Methode 1 | Draufsicht unter, Seitenansicht von links rechts neben der Vorderansicht, fluchtend | – | C, unbelegt | ja – Z (`IView.Position`, `GetOutline`) |
| Symbolgeometrie Kegelstumpf (Kreis rechts der Trapezansicht, Höhe ≈ 2h); Pfeilmethode für abweichende Anordnung | – | – | C, unbelegt | – |
| Drehteil: eine Ansicht mit Ø genügt, Achse waagerecht; keine Ansicht ohne eigene Information | – | – | C, unbelegt (Praxis) | teilweise – S (`rotation`) |

### Schnitte und Schraffur (ISO 128-3)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Schraffurwinkel | 45° bzw. 135° zur Hauptkante oder Symmetrielinie | [Wikipedia DE TZ](https://de.wikipedia.org/wiki/Technisches_Zeichnen); [mechatronik-automatisierung.com](https://mechatronik-automatisierung.com/technische-doku/zeichnung-lesen/schnitte/) | A | ja – Z (`IView.GetFaceHatches` → `IFaceHatch.Angle`) |
| Schraffurabstand | gleichmäßig, an Flächengröße angepasst (kein Zahlenwert belegt) | Wikipedia DE TZ; mechatronik-automatisierung.com | A | teilweise – Z (`IFaceHatch.Scale2`) |
| Schraffurlinie | schmale Volllinie | lehrerfreund; Wikipedia DE TZ | A | ja – V |
| gleiches Teil gleiche Schraffur; Nachbarteile durch Richtung/Abstand unterscheidbar; werkstoffneutral, Werkstoff im Schriftfeld | – | mechatronik-automatisierung.com | B | ja – Z (Baugruppe: Schraffur je Komponente vergleichen) |
| dünne Querschnitte (Blech, Dichtung) | geschwärzt, Nachbarn durch weißen Spalt getrennt | mechatronik-automatisierung.com | B | – |
| verdeckte Kanten im Schnitt | weglassen | mechatronik-automatisierung.com; Wikipedia DE TZ | A | ja – Z (`SetDisplayMode4` der Schnittansicht) |
| nicht längs geschnitten | Rippen, Stege, Speichen, volle Wellen und Achsen, Schrauben, Muttern, Bolzen, Stifte, Niete, Keile, Passfedern, Zahnzähne, Wälzkörper; im Querschnitt normal schraffiert; Schraffur nicht versetzen | mechatronik-automatisierung.com (Notiz 01); TUM Zeichnungserstellung (Suchauszug, Notiz 04); Suchauszüge GWS Lörrach, HS Schmalkalden | B | teilweise – S (Normteile über `quelle: normteil`; Wellen, Rippen bräuchte Spec-Kennzeichen); Z (`IDrSection.GetExcludedComponents`) |
| Schnittverlauf und Bezeichnung | Strichpunktlinie, an Enden/Knicken breit; Blickpfeile; Buchstabenpaar; Überschrift „Schnitt A–A“; fortlaufend A–A, B–B | mechatronik-automatisierung.com | B | ja – Z (`IDrSection.SetLabel2`, Bezeichnung mit Schnittlinie abgleichen) |
| Schnittbuchstaben vom Alphabetanfang, Einzelheiten vom Ende (Z, Y, X); Schnittverlauf nur zeichnen, wenn nicht eindeutig | – | [TUM Zeichnungserstellung](https://www.epe.ed.tum.de/fileadmin/w00bzo/ewt/Werkstatt/Zeichnungserstellung.pdf) (Suchauszug) | B | ja – Z |
| Schnittarten | Voll-, Halb-, Teilschnitt/Ausbruch (Freihand-/Zickzackgrenze), versetzter Schnitt, umgeklappter Profilschnitt | mechatronik-automatisierung.com; Wikipedia DE TZ | A (Arten), B (Einzelheiten) | – |
| Halbschnitt nur bei symmetrischen Teilen | – | mechatronik-automatisierung.com | B | teilweise – S (Symmetrie aus `bezug: mitte`/`spiegeln`) |
| Schraffurabstand ≥ 0,7 mm, typ. 2–4 mm; Seite des Halbschnitts; „A–A“ vs. „A-A“; Buchstaben ohne I, O, Q | – | – | C, unbelegt | – |

### Einzelheiten, Unterbrechung, Vereinfachung

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Maßstab der Einzelheit steht bei der Einzelheit | – | [ingenieurkurse Maßstäbe](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/massstaebe-nach-din-iso-5455.html); [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/) | A | ja – Z (`CreateDetailViewAt4` Scale1/2, Beschriftung) |
| Bezeichnung Einzelheit | Großbuchstaben rückwärts Z, Y, X … | TUM Zeichnungserstellung (Suchauszug) | B | ja – Z |
| Einzelheitenkreis schmale Volllinie, Überschrift „Z (5:1)“ | – | – | C, unbelegt | – |
| Bruchlinie unterbrochener Ansicht | schmale Freihand- oder Zickzacklinie | Wikipedia DE TZ; lehrerfreund | A | ja – Z (`IView.InsertBreak3`) |
| Regelort | früher DIN ISO 128-34:2002-05 „Unterbrochene Ansichten“, jetzt ISO 128-3 | Suchauszug DIN-TOC; Wikipedia EN ISO 128 | B | – |
| Maße laufen über die Unterbrechung, Maßzahl = wahres Maß; Lückenweite | – | – | C, unbelegt | ja – Z (Maßwert = `GetSystemValue3`) |
| Vereinfachte Darstellung Maschinenbau | ISO/TS 128-71:2010 | [Wikipedia EN ISO 128](https://en.wikipedia.org/wiki/ISO_128) | B | – |
| Symmetriezeichen (zwei kurze Parallelstriche); wiederholte Elemente nur einmal voll, Rest Mittellinien; Lichtkante endet vor Umriss | – | – | C, unbelegt | – |

## 4. Bemaßung nach ISO 129-1

Frei lesbarer ISO-129-1-Text wurde nicht gefunden. Belegt sind Gliederung und Geltungsbereich, außerdem Lehr- und Praxisregeln, oft aus der DIN-406-Zeit. Die meisten Detail-Schreibregeln sind C. Sie gehören vor einer Umsetzung an die Vorschau von ISO 129-1 (Kap. „Quellen, die die Belegstärke heben würden“).

### Grundsätze und Maßelemente

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Gliederung ISO 129-1 | Maße, wiederholte Maße, Hilfsmaße, theoretisch genaue Maße, symmetrische Maße, Anordnung, Einheiten; 5.3 Maßlinie; deckt Koordinatenmaße, Bohrungen, Gewinde, Kegel, wiederkehrende Elemente, Symmetrie ab | [DIN TOC](https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:333197796/toc-3331584/download) (Suchauszug); [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-129-1/333197796) | B | – |
| Bedeutung von Toleranzen | nicht in ISO 129-1, sondern ISO 14405-1 | [ISO 64007](https://www.iso.org/standard/64007.html); DIN Media | A | – |
| Leserichtung | von unten oder von rechts lesbar (Methode 1) | [Wikibooks Maßeintragung](https://de.wikibooks.org/wiki/Technisches_Zeichnen/_Ma%C3%9Feintragung); TUM (Suchauszug) | B | ja – Z (Textwinkel aus `GetDimensionDisplayInfo5`) |
| Maßzahl | mittig über der Maßlinie | [schule-bw.de](https://schule-bw.de/resolveuid/55248110505c4e37b9ea1eec8c92beac) (Suchauszug) | B | ja – Z (`CenterText`) |
| Maßhilfslinie | ca. 2 mm über den Maßpfeil hinaus | TUM (Suchauszug) | B | ja – V |
| Maßpfeil | 15° Öffnungswinkel; gefüllt nicht ausdrücklich belegt | TUM (Suchauszug) | B | ja – V |
| Maßlinienbegrenzung | Pfeile; bei Platzmangel Punkte oder Schrägstriche | [Wikipedia DE Bemaßung](https://de.wikipedia.org/wiki/Bema%C3%9Fung) (DIN 406) | B | ja – V/Z |
| Einheiten | Längen ohne Einheit (mm); bei mehreren Einheiten Standardeinheit nahe Schriftfeld; Winkel immer mit Einheit; ohne Toleranzzusatz gilt die Allgemeintoleranz | Wikipedia DE Bemaßung | B | ja – V (`swUnitsLinear`) |
| nicht maßstäblich | Maßzahl unterstrichen | Wikipedia DE Bemaßung; [item24](https://glossar.item24.com/en/glossary-index/article/item//dimensioning.html) (Suchauszug) | A | ja – Z (Maßwert gegen gezeichnete Länge) |
| Hilfsmaß | runde Klammern, errechenbar aus anderen Maßen, nicht maßgebend; ISO „(50)“, ASME zusätzlich „REF“ | [werk24](https://werk24.io/blog/iso-vs-asme-technical-drawing-standards-complete-comparison); [Wikipedia EN Abbreviations](https://en.wikipedia.org/wiki/Engineering_drawing_abbreviations_and_symbols); Suchzusammenfassung DIN 406 | B (ISO-Bedeutung, Notiz 02), A (Klammerform); Notiz 05: C | ja – Z (`IDisplayDimension.ShowParenthesis`, `IsReferenceDim`) |
| Prüfmaß | abgerundeter Rahmen = Maß besonderer Bedeutung, nach Fertigung zu prüfen (DIN 406; Übernahme in ISO 129-1:2018 offen) | Wikipedia DE Bemaßung | B (Notiz 02); Notiz 05: C | ja – Z (`IDisplayDimension.Inspection`) |
| theoretisch genaues Maß (TED) | rechteckiger Rahmen, ohne Toleranz; in ISO 1101 geführt; ältere ISO 129 hat Abschnitt „Theoretisch exakte Maße“ | [DGQ Symbole](https://formativ.dgq.de/wp-content/uploads/2023/11/DGQ_ISO-GPS_Symbole-und-Abkuerzungen_2023_11_01.pdf) (Suchauszug, Notiz 05: B nur Existenz); ASME „basic“ B | C für Rahmenform in ISO (Notiz 02) | ja – Z (`swTolType_e` BASIC) |
| Abstand erste Maßlinie zur Körperkante | 10 mm | Wikibooks; [schule-bw.de](https://schule-bw.de/resolveuid/6051e1eb3c8f4608a14afb7cafe79872) (Suchauszug) | B | Hausregel – Z |
| Abstand weiterer Maßlinien | 7 mm (Wikibooks) vs. 5 mm (schule-bw) | Wikibooks; schule-bw.de | B (Widerspruch) | Hausregel – Z (`AlignDimensions` SpaceEvenly) |
| führende Null | „optional (0.5 or .5)“ laut werk24, widerspricht ISO-Praxis | werk24 | B, zweifelhaft | – |
| jedes Maß nur einmal; keine geschlossenen Maßketten (Kettenglied weglassen oder Hilfsmaß); Maß in der Ansicht mit deutlichster Form | – | – | C (Notiz 02); Grundsatz durch Notiz 05 als A belegt (s. u.) | ja – Z/S (Maßgraph je Richtung) |
| Maßlinien nicht an verdeckte Kanten; Maßlinien nicht kreuzen; Mittellinien/Kanten nicht als Maßlinie, aber als Maßhilfslinie | – | – | C, unbelegt | ja – Z (`GetAttachedEntities3`, Sichtbarkeit über `GetVisibleEntities2`) |
| Pfeil ≈ 10 × Linienbreite, gefüllt/offen; nur eine Pfeilart je Zeichnung; Ursprungskreis bei steigender Bemaßung | – | – | C, unbelegt | – |
| Methode 1 (ausgerichtet) vs. Methode 2 (waagerecht) – nur eine je Zeichnung | – | – | C, unbelegt | – |
| Dezimalkomma; führende Null immer (0,5); Winkel mit °, ′, ″ | – | – | C, unbelegt | teilweise – V (Komma hängt an Systemoption, Kap. 10) |

**Widersprüche:**
- Der Abstand weiterer Maßlinien ist 7 mm laut Wikibooks und 5 mm laut schule-bw. Keine der Quellen nennt eine Norm, der Wert ist also eine Hausregel.
- Das item24-Glossar vermischt Prüfmaß (abgerundeter Rahmen) und theoretisch genaues Maß (rechteckiger Rahmen). Ein Prüfer muss beide Rahmenformen unterscheiden.

### Maßbezugssysteme, Ketten- und Koordinatenbemaßung, Überbestimmung

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Bezugs- statt Kettenbemaßung | Bezugsbemaßung von gemeinsamer Referenz verringert Toleranzaddition; Kette „judiciously“ | [Cambridge Network](https://www.cambridgenetwork.co.uk/index.php/news/art-dimensioning-cad-drawings-cnc-machining-traditional-fraftsmans-approach); [buffl.co](https://buffl.co/community/c/6946dd6ba18ba13579567696); RUB (Suchauszug) | A | ja – S (`bezug` je Lage) + Z (Maßanker je Richtung) |
| jedes Maß nur einmal; keine Überbemaßung | Maß, das schon durch andere bestimmt ist, ist Überbemaßung | [TUM](https://www.epe.ed.tum.de/fileadmin/w00bzo/ewt/Werkstatt/Zeichnungserstellung.pdf) (Suchauszug); buffl.co; [Fictiv](https://www.fictiv.com/articles/9-tips-for-better-engineering-drawings-that-save-time-money) | A | teilweise – S (je Skizze plant `swki/bemassung.py` `massplan` ohne Überbestimmung); featureübergreifend bräuchte Z (Maßgraph je Achse = Baum) |
| unterbrochene Kette | Gesamtmaß angeben, ein Teilmaß weglassen; Kette nur für unkritische Merkmale | [WTCS](https://wtcs.pressbooks.pub/blueprintreading/?p=154) (Suchauszug) | B | ja – Z |
| Toleranzrechnung Kette | Worst Case = Summe; statistisch = Wurzel der Quadratsumme | [Hexagon tol1_d](https://www.hexagon.de/pdf/tol1_d.pdf); [CASIM](https://www.casim.de/wp-content/uploads/2018/08/Komplexe_Toleranzanalyse.pdf) (Suchauszüge) | B | nein – bräuchte Toleranzen in S |
| funktions-, fertigungs-, prüfbezogen | Dreiteilung aus DIN 406-10/-11 (zurückgezogen), in der Lehre kombinierbar | [RUB fertigungsgerechte Bemaßung](https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598368/mod_resource/content/9/Beschreibung%20fertigungsgerechte%20Bema%C3%9Fung_meta_lizenz.pdf) (Suchauszug) | B | – |
| ISO 129-1 deckt Koordinatenmaße ab | – | DIN Media | B | – |
| Ketten-, Parallel-, steigende, Koordinatenbemaßung im Einzelnen (Ursprung als offener Kreis mit 0, Koordinatentabelle Pos./X/Y/Ø, Polarkoordinaten) | – | – | C, unbelegt | – |
| Abbildung auf swki | `bezug: {flaeche}`/`-rand`/`+rand` → Parallel- bzw. steigende Bemaßung von Bezugskante; `mitte` → symmetrisch zur Mittellinie; `ursprung` → Koordinatenbemaßung | Folgerung (Notiz 02/05) | C | ja – S |

### Symbole

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| SR = Kugelradius, R = Radius | SR30, R6 | [werk24 Symbols](https://werk24.io/knowledge-base/symbols) (Suchauszug); [Wikipedia EN](https://en.wikipedia.org/wiki/Engineering_drawing_abbreviations_and_symbols) | A | ja – Z (Maßtext) |
| vorangestellte Zeichen | Ø Durchmesser, R Radius, S Kugel (SØ/SR), ⌒ Bogenlänge, □ Quadrat | [Wikipedia DE Bemaßung](https://de.wikipedia.org/wiki/Bema%C3%9Fung) (DIN 406) | B | ja – Z |
| CR (kontrollierter Radius) | nur ASME | Wikipedia EN | B | Prüfregel „nicht verwenden“ – Z |
| ⌴ (Senkung), ⌵ (Kegelsenkung), ↧ (Tiefe) | in ASME Y14.5M-1994 für ISO nur „proposed“; Praxis mischt Symbole und Texte CBORE/CSK/DEEP; ob ISO 129-1:2018 sie enthält, unbelegt | [Eng-Tips](https://www.eng-tips.com/threads/basic-dimensioning-of-holes-cbores-amp-csinks-per-iso-standard.228508) (Suchauszug) | B (Altlage); C (ISO 129-1:2018) | Hausregel – Z |
| Anzahl | „8X“ oder „(8)“ (ASME, ohne Leerzeichen); werk24: „4X Ø8“ für ISO und ASME | Wikipedia EN; werk24 | B | Hausregel – Z |
| Anzahl DE-Praxis „6 × Ø8“; ⌒ vor der Zahl seit ISO 129-1:2018; „t=3“ (DIN 406-11), „C“ als 45°-Fase in ISO 129-1:2018; R nur bis 180°, sonst Ø; Ø immer setzen | – | – | C, unbelegt | – |

**Widersprüche:** werk24 gibt als ISO-Tiefensymbol „⌀15“ an, offensichtlich falsch. Die Quelle ist bei ISO-Details unzuverlässig. Ein Eng-Tips-Beitrag (Suchauszug, C) deutet an, dass ISO 129-1 ein Kegelsenkungssymbol hat, ISO 15786 nicht.

### Bohrungen, Bohrbilder, Muster

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| ISO 15786 regelt vereinfachte Darstellung, Bemaßung, Tolerierung von Bohrungen, Senkungen, Innengewinden, Fasen | – | [ISO 42099](https://www.iso.org/standard/42099.html); [standards.ie](https://shop.standards.ie/en-ie/standards/bs-iso-15786-2008-213688_saig_bsi_bsi_504656) | A | – |
| Kernloch breite Volllinie, Bohrerspitze 120° | – | [Frankfurt UAS](https://campuas.frankfurt-university.de/mod/resource/view.php?id=263332) (Suchauszug) | B | ja – M (Spitze aus Modell) |
| Senkungsbeispiele „⌴ Ø16 …“, „⌵ 90° Ø12“ | – | werk24 (unzuverlässig) | B | – |
| Senkung mit Normverweis „Senkung 90° DIN 74-1“ | – | [hausjournal.net](https://hausjournal.net/gewinde-bemassen) (niedrige Qualität) | B | – |
| Bohrungstiefe = zylindrischer Teil ohne Spitze; ISO-15786-Schreibweise „Ø10 × 20“, „Ø6,6 × 20 / Ø11 × 6,4“, „Ø6,6 / Ø12 × 90°“; „×“ oder „↧“ offen; Angabe mit Hinweislinie in der Draufsicht | – | – | C, unbelegt | ja – S (`bohrung`/`normbohrung`: `durchmesser`, `tiefe`, `durch`, `senkung`) gegen Z (`IsHoleCallout`, Text) |
| wiederholte Maße, wiederkehrende Elemente | in ISO 129-1 geregelt (Schreibweise nicht gelesen) | DIN Media; DIN TOC (Suchauszug) | A | – |
| gleiche Merkmale zusammenfassen | eines bemaßen, Anzahl angeben („4X …“); Vorsicht bei ähnlichen Größen | [Fictiv Tip 3](https://www.fictiv.com/articles/9-tips-for-better-engineering-drawings-that-save-time-money) | B | ja – S (`positionen`-Anzahl, `muster_*` `anzahl`) gegen Z |
| Lochabstand gleicher Bohrungen funktionsgerecht direkt bemaßen | – | RUB (Suchauszug) | B | teilweise – S (Abstand als `parameter`) |
| PCD = Teilkreis-Ø; EQ/EQS = gleichmäßig verteilt | – | Wikipedia EN | B | – |
| „6 × Ø8“; „5 × 20 (= 100)“ mit Gesamtmaß als Hilfsmaß; „8 × 45° (= 360°)“; Teilkreis schmale Strichpunktlinie mit Ø; Koordinatentabelle ab ca. 8–10 Bohrungen | – | – | C, unbelegt | ja – S/Z |

Hausstil-Bezug: Bohrbilder werden im Modell nur für Reihen ab 3 Löchern gemustert, Paare und Lochkreise bleiben `positionen` mit `bezug: mitte`. Für die Zeichnung ist die Anzahl in beiden Fällen gleich zu schreiben. swki kennt sie aus `positionen` bzw. `anzahl`.

### Fasen und Radien

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| geometrisch bestimmte Kante (z. B. „1 × 45°“) wird nach ISO 129-1 bemaßt | Wortlaut ISO 13715-Abstract | [BSI](https://knowledge.bsigroup.com/products/technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning) (Suchauszug) | B | – |
| zwei Schreibweisen | „C3“ (45°, Schenkel 3) und „0,5 × 45°“ bzw. „0,8 × 30°“ | [werk24 Edges](https://werk24.io/knowledge-base/edges) | B | Hausregel – Z |
| „C2“ und „2 × 45°“ unter ANSI und ISO zulässig | ohne Klauselbeleg | [brainbound](https://www.brainbound.blog/chamfer-notation-guide) (schwach) | B | – |
| Praxis uneinheitlich | Zeiss-Forum fragt, wozu „C“ neben „1 × 45°“ | [Zeiss Quality Forum](https://qualityforum.zeiss.com/topic/5842-radiuses-and-chamfers-with-c-t-symbol/) | B | – |
| Kurzform nur für 45° | einig in werk24 und brainbound | werk24; brainbound | B (Notiz 02: je B, Regel selbst unter C) | ja – S (`fase` am Feature: Winkel) |
| Maß = Schenkellänge, nicht Hypotenuse; Radius: Maßlinie vom/zum Mittelpunkt, ein Pfeil, Z-Knick bei fernem Mittelpunkt | – | – | C, unbelegt | – |
| Hausstil Fasen | nur an Bohrungseintritten 0,5 × 45° (Gewinde: Ansenkung auf Nenn-Ø), Außen-, Anlage- und Passkanten ohne Fase | Skill `konstruieren`, Regel 6 | (Hausregel) | ja – S (`fase` an `bohrung`/`normbohrung`) |
| Hausstil Innenradien | gefräste Innenecken R ≥ T/5 | Skill `konstruieren`, Regel 8 | (Hausregel) | ja – S/M (`validieren` meldet heute schon `fertigung`-Hinweise) |

**Widersprüche:** Für Fasen ≠ 45° schreibt werk24 „Länge × Winkel“, brainbound verlangt zwei getrennte Längenmaße. Daraus folgt (Notiz 02): sicherer Standard ist „0,5 × 45°“ (in DE verbreitet, durch den Verweis in ISO 13715 gedeckt), „C0,5“ nur als Option.

### Toleranzschreibweise am Maß

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| symmetrisch | „50 ± 0,1“, Zeichen ±; ASME auch „+/-“ | [werk24](https://werk24.io/blog/iso-vs-asme-technical-drawing-standards-complete-comparison) | B | ja – Z (`IDimensionTolerance.Type`) |
| Gewinde mit Toleranz | „M8x1.25-6H“ | werk24 | B | ja – Z |
| Abmaße hinter Nennmaß, oben/unten, gleiche Nachkommastellen, 0 ohne Vorzeichen, Schrift ≥ 2,5 mm; Grenzmaße; „Ø20H7“, „Ø20H7/g6“, „Ø20H7 (+0,021/0)“; „max“/„min“ | – | – | C, unbelegt | nein – bräuchte Toleranzfeld in S |

## 5. Gewinde (ISO 6410) und Kanten (ISO 13715)

### Gewinde

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Innengewinde Stirnansicht | ein Durchmesser als ¾-Kreis in schmaler Volllinie (welcher, ist widersprüchlich) | [hausjournal.net](https://hausjournal.net/gewinde-bemassen); [Christiani](https://www.lehmanns.ch/media/87204491) (Suchauszug) | B | teilweise – Z (kosmetisches Gewinde in Ansicht: `swInsertCThreads`, `SetDisplayMode4` CThreadHighQuality) |
| Bezeichnung | Feingewinde „M24×1,5“; Linksgewinde „LH“ hinter der Bezeichnung; Toleranzklasse z. B. „6g“; „M8x1.25-6H“ | hausjournal.net; [werk24](https://werk24.io/blog/iso-vs-asme-technical-drawing-standards-complete-comparison) | B | ja – S (`normbohrung` `groesse`, z. B. „M10x1“) gegen Z (`ICosmeticThreadFeatureData.ThreadCallout`) |
| Sackloch | Bohrtiefe ≈ 1,25 × Gewindetiefe (Faustregel) | hausjournal.net (Ratgeber) | B | ja – S (`tiefe`, `gewindetiefe`) |
| Kernloch | größer als Kerndurchmesser gebohrt | [tutory](https://www.tutory.de/entdecken/dokument/gewindeschneider-1.pdf?t=2128) (Suchauszug) | B | – (Bohrungsnormen aus `swki/wissen/bohrungsnormen.yaml`) |
| CAD-Strichlinien für Gewinde | Software-, nicht Normdarstellung | [Onshape-Hilfe](https://cad.onshape.com/help/de_DE/Content/PartStudio/external_thread.htm) | B | P |
| Gewindespitzen breit, Gewindegrund schmal (Abstand ≥ 0,7 mm); ¾-Kreis = Gewindegrund, Lücke rechts oben, Fasenkreis nicht zeichnen; Gewindebegrenzung breit quer; Auslauf nicht zeichnen; Schraffur bis zur breiten Linie; Gewindetiefe bemaßen, Bohrtiefe nur wenn funktional; vereinfachte Darstellung kleiner Gewinde nach ISO 6410-3 („M6 × 12 / Ø5 × 16“, unsicher) | – | – | C, unbelegt | – |

**Widersprüche:** hausjournal.net zeichnet den *Gewinde*durchmesser als ¾-Kreis, das Christiani-Arbeitsblatt (Suchauszug) den *Kern*durchmesser. Nach Hintergrundwissen (C, ISO 6410-1) ist der ¾-Kreis immer der Gewindegrund, also beim Innengewinde der Nenndurchmesser.

### Kanten (ISO 13715)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Vorzeichen | „+“ = zulässiger Materialüberschuss (Grat außen, Übergang innen); „−“ = geforderte Materialabtragung; „±“ = beides, nur mit Größenangabe | [modulusmetal](https://www.modulusmetal.com/iso-13715-technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning); [werk24 Edges](https://werk24.io/knowledge-base/edges) | A | ja – Z (Notiz/Symboltext) |
| Zahl | Größe a gegenüber idealer scharfer Kante | werk24; modulusmetal | A | ja – Z |
| Normumfang | Symbole für Außenkanten (ohne/mit begrenztem Grat), Innenkanten mit Übergang, Proportionen; Gliederung „Basic indication“, „Types of undefined edge“, „Size“, „Direction of passing or undercut“ | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-13715/314070606); [BSI](https://knowledge.bsigroup.com/products/technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning) | A | – |
| Begriffswandel | Ausgabe 2017 fasst Außengrat unter „passing“; ältere trennen „burr“/„passing“; 1994 mit „corner“-Begriff | modulusmetal; Suchauszug iteh 1994 | B | – (Bestandszeichnungen beachten) |
| Richtungsangabe | für Abtragung außen bzw. Übergang innen nicht zulässig (Ausgabe unklar) | Suchauszug | B | – |
| Sammelangabe | gilt für alle Kanten, sofern nicht örtlich überschrieben; Beispiel „All edges: ±0.2; outer profile: +0.3 max; slot S1: −0.1 max“ | werk24 Edges | B | ja – Z (höchstens eine Sammelangabe je Blatt; jeder Wert mit Vorzeichen; ± nie ohne Zahl) |
| CAD-Umsetzung | Richtung waagerecht/senkrecht/unbestimmt; Ober-/Untergrenze nur bei unbestimmter Richtung; Rundum; Sammelsymbol („Majority symbol“); optional Normverweis „ISO 13715“ | [Autodesk Fusion](https://help.autodesk.com/cloudhelp/ENU/Fusion-Drawing/files/DWG-REF-EDGE-SYMBOL.htm); AutoCAD Mechanical (Suchauszug) | B | – |
| Lage der Sammelangabe nahe Schriftfeld, Ausnahmen in Klammern; DE-Praxis „−0,1 … −0,3“ bzw. „−0,3“ für „entgratet“; Werte-Tabelle (+0,3; +0,1; −0,1; −0,3) | – | – | C, unbelegt | – |

Folgerungen:
- Die neue ISO 2768 (Entwurf) streicht die Toleranzen für gebrochene Kanten, Fasen und Radien (Kap. 7). Die Kantenangabe nach ISO 13715 wird damit wichtiger.
- Der Hausstil lässt Außen-, Anlage- und Passkanten ohne Fase. Ihr Zustand (scharf, entgratet) steht deshalb nur in der Sammelangabe.
- Für ISO 13715 wurde keine SolidWorks-API gefunden (Kap. 10). Die Angabe bräuchte eine Notiz oder einen Symbolblock in der Vorlage.
- Die Spec hat kein Feld für den Kantenzustand.

## 6. Oberflächen (ISO 21920)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| ISO 21920-1 ersetzt ISO 1302 | DIN EN ISO 21920-1:2022-12 | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-21920-1/344762052); [BSI](https://knowledge.bsigroup.com/products/geometrical-product-specifications-gps-surface-texture-profile-indication-of-surface-texture) (Suchauszug) | A | ja – V (`swDetailingSFSymbolStandard` = 21920_1) |
| Annahmeregel | **Max-Regel ist Standard**; 16-%-Regel nur, wenn ausdrücklich angegeben | [Digital Surf Guide](https://guide.digitalsurf.com/en/guide-iso-21920-parameters.html); [Quality Magazine](https://www.qualitymag.com/articles/98952-evolving-roughness-standards-understanding-and-implementing-iso-21920); DIN Media | A | ja – Z (Symboltext) |
| neues Symbol | Strich über dem Dreieck links am Wurzelzeichen; neues Symbol → ISO 21920, altes → ISO 1302/4287/4288; Kenngröße und Grenzwert zuerst, Rest nach Schrägstrich | [Digital Surf Blog](https://www.digitalsurf.com/blog/how-is-surface-texture-indicated-on-drawings/); Digital Surf Guide (ein Hersteller) | B | ja – Z/V |
| Begriffe | Kenngrößen über die Auswertelänge (Ausnahme Rp, Rv, Rz: über Abschnitte gemittelt); „section length“ lsc statt „sampling length“; Rz = „maximum height“; periodisch/aperiodisch entfällt; Unvollkommenheiten nicht mehr ausgespart | Digital Surf Guide; Quality Magazine | A | – |
| Standardfilter | aus der Spezifikation (für Ra, Rq, Rz aus dem Toleranzwert), nicht aus der Geometrie; Einstellungsklassen Sc1–Sc5 | Quality Magazine | B | – |
| Einstellungsklassen (λc / Auswertelänge / Abschnittslänge) | Sc1 Ra ≤ 0,02 µm: 0,08 / 0,4 / 0,08 mm; Sc2 ≤ 0,1: 0,25 / 1,25 / 0,25; Sc3 ≤ 2: 0,8 / 4,0 / 0,8; Sc4 ≤ 10: 2,5 / 12,5 / 2,5; Sc5 > 10: 8,0 / 40,0 / 8 | Quality Magazine | B (Quellenfehler beim S-Filter, nur mit Norm verwenden) | – |
| Übergang | alte Zeichnungen bleiben gültig (nach ISO 1302/4287/4288 lesen); Annahmeregel ausdrücklich angeben | Quality Magazine | B | ja – Z (gemischte alte/neue Symbole melden) |
| undatierter Verweis „ISO 1302“ | führt auf ISO 21920 | [GPSlife](https://gpslife.de/en/?p=1417) | B | ja – Z |
| Ra nach Verfahren (Reihenfolge) | Läppen < Honen < Schleifen < Reiben < Drehen ≈ Fräsen < Bohren | [JLCCNC](https://jlccnc.com/blog/surface-roughness); Suchauszüge | A (Reihenfolge) | – |
| Ra nach Verfahren (µm) | Drehen 0,8–6,3; Fräsen 0,8–6,3; Bohren 3,2–12,5; Reiben 0,4–1,6; Schleifen 0,2–1,6; Honen 0,1–0,8; Läppen 0,025–0,2 | JLCCNC | B (andere Quellen streuen deutlich) | – |
| N-Klassen | N5 = Ra 0,4 … N10 = 12,5 µm; alte ISO 1302:1992, nicht mehr normgerecht | JLCCNC | B | ja – Z (N-Angabe melden) |
| RWDR-Lauffläche (DIN 3760/3761) | Ra 0,2–0,8 µm, Rz 1–5 µm (DIN 3760) bzw. 1–4 µm (DIN 3761), Rmax ≤ 6,3 µm, drallfrei | [Uni Stuttgart IMA](https://www.ima.uni-stuttgart.de/dokumente/forschung/dichtungstechnik/dienstleistungen/104170.pdf); [Dichtomatik](https://www.fst.com/de/-/media/files/dichtomatik/solution-sheets/de/dichtomatik_radial-wellendichtringe.pdf) (Suchauszüge) | B | nein – bräuchte Funktionsflächen in S |
| Wälzlager-Passflächen | Ra Welle 0,8 / Gehäuse 1,6 (kleine Lager); 1,6 / 3,2 (große); Einheit µm angenommen | [JTEKT](https://www.jtekt.co.jp/products/bearing/en/support/bearing-knowledge/14-1000.html) | B | nein – bräuchte S |
| Funktionsbeispiele | Ra 0,4 Laufbahnen/Präzisionswellen; 0,8 Lagersitze, Hydraulik, Dichtflächen; 1,6 Lagersitze, Fügeflächen; 3,2 Standard-CNC | JLCCNC | B | – |
| Sammelangabe „√Ra 3,2 (√)“ in Schriftfeldnähe; Ra 1,6 Passflächen/Anlageflächen, 0,8 Wellen-Lagersitze/H7-Bohrungen; Elementpositionen a–e am Symbol; Notation 16-%-Regel; Komma vs. Punkt | – | – | C, unbelegt | – |

**Widersprüche:**
- Der Digital-Surf-Blog nennt als Standard die 16-%-Regel und als Auswertelänge 5 × λc. Das ist der Stand ISO 1302/4288 und für ISO 21920 überholt.
- Quality Magazine gibt den S-Filter als „2,5 / 2,5 / 2,5 / 8 / 25 mm“ an. Neben λc = 0,08 mm ist das unmöglich, gemeint ist vermutlich µm.
- Für Bestandszeichnungen mit altem Symbol gilt die 16-%-Regel. Eine gleiche Ra-Zahl ist unter ISO 21920 faktisch strenger (Folgerung, Notiz 03).

## 7. Toleranzen

### Allgemeintoleranzen (ISO 2768-1, ISO 22081, DIN 2769)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| ISO 2768-2 zurückgezogen | 04.02.2021, Nachfolger ISO 22081:2021 | [genorma](https://genorma.com/en/standards/iso-2768-2-1989); [Wevolver](https://www.wevolver.com/article/iso-2768-general-tolerances-tables-classes-current-status) | A | ja – Z (Vermerk „ISO 2768-…K/H/L“ als Befund melden) |
| Folge undatierter Verweise | „ISO 2768-mK“ (seit 2021) bzw. „DIN ISO 2768-2“ (seit 2022) wird als ISO 22081 gelesen; diese verlangt explizite Werte → keine wirksamen Form-/Lage-Allgemeintoleranzen; Normnummer datieren, wenn Ausgabe gemeint | [GPSlife](https://gpslife.de/en/?p=1417); Wevolver | A | ja – Z |
| ISO 22081 als „fälschlich“ gekennzeichneter Ersatz | laut DIN-Einführung | [din.de TOC](https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:356826589/toc-3371761/download) (Suchauszug) | B | – |
| Inhalt ISO 22081 | keine Zahlenwerte; allgemeine geometrische Spezifikation = Flächenprofil auf ein Bezugssystem; Wert einheitlich oder abhängig von Größe bzw. Abstand zum Bezugssystem; Abschnitt 5.3 Bezugssystem, Anhang B Beispiele | [iteh](https://standards.iteh.ai/catalog/standards/iso/5bb1f91d-50a4-44cf-bdbf-3652b92dd8ee/iso-22081-2021); [Hexagon 049-FMT](https://bynder.hexagon.com/m/6acb6f81db21e367/original/049-FMT_Allgemeintoleranzen-nach-ISO-22081.pdf); [IHK](https://www.ihk.de/blueprint/servlet/resource/blob/5831308/d01f30113d287172380e5da5f9cefce1/gps-allgemeine-toleranzen-data.pdf) (Suchauszüge) | B | nein – bräuchte Bezugssystem in S |
| Bezugssystem der allgemeinen Spezifikation | muss alle für die Ortsfestlegung nötigen Freiheitsgrade sperren; gilt nicht für die Bezugselemente selbst | IHK (Suchauszug); Wevolver | B | nein – bräuchte S |
| ISO 22081 und ISO 8015 | allgemeine Spezifikationen „defined according to ISO 8015:2011“ | Wevolver | B | – |
| allgemeine Spezifikationen | im oder nahe dem Schriftfeld eindeutig angeben | iteh (Suchauszug) | B | ja – Z |
| DIN 2769:2023-04 | Werte in Toleranzklassen zu ISO 22081; technologie-, material-, teileunabhängig; „löst als Nachfolger die Normenreihe DIN ISO 2768 ab“; Klassen A bis E (Suchauszug), Werte nicht gefunden | [DIN Media](https://www.dinmedia.de/de/norm/din-2769/364625893); IHK (Suchauszug) | B | – |
| Entwurf DIN 2769:2026-09 | Kopplung an 3D-Modell (DIN ISO 16792:2025-06); Anhänge B (D0), C (Modellwerte, TED), D (Modifikator „add“) | [DIN Media Entwurf](https://www.dinmedia.de/de/norm-entwurf/din-2769/404718083) | B | – |
| neue ISO 2768 (Entwurf 2025-09) | vier Klassen; Größenmaße > 0,5 bis 4000 mm und Winkel; Zweipunktmaß; mit ISO 22081 kombinierbar; „Zurückweisung“ (Abschnitt 6) gestrichen; **Fasen, Radien, gebrochene Kanten gestrichen** | [DIN Media Entwurf](https://www.dinmedia.de/de/norm-entwurf/din-en-iso-2768/394170392) | B | ja – Z (künftig: Fase/Radius ohne eigene Toleranz melden) |
| Zurückweisung ISO 2768-1:1989 | nur, wenn Funktion beeinträchtigt; TED von Allgemeintoleranzen ausgenommen | Wevolver | B | – |
| Nennmaße < 0,5 mm | Grenzabmaße direkt am Maß | Wevolver; TUM (Suchauszug) | A | ja – S/Z |
| Eintrag „ISO 2768-m“ | gilt für alle nicht einzeln tolerierten Maße | [Wikipedia DE Allgemeintoleranz](https://de.wikipedia.org/wiki/Allgemeintoleranz) | B | ja – Z |
| „ISO 2768-mK-E“ | Hülle für alle Einzel-Formelemente | Wevolver; Wikipedia DE | A | – |

ISO 2768-1:1989, Tabelle 1, Längenmaße außer gebrochenen Kanten (Grenzabmaße in mm) – **A** ([amesweb](https://amesweb.info/fits-tolerances/iso-2768-linear-dimensions-tolerances.aspx); [Wevolver](https://www.wevolver.com/article/iso-2768-general-tolerances-tables-classes-current-status)):

| Nennmaß (mm) | f | m | c | v |
|---|---|---|---|---|
| 0,5 bis 3 | ±0,05 | ±0,1 | ±0,2 | – |
| über 3 bis 6 | ±0,05 | ±0,1 | ±0,3 | ±0,5 |
| über 6 bis 30 | ±0,1 | ±0,2 | ±0,5 | ±1 |
| über 30 bis 120 | ±0,15 | ±0,3 | ±0,8 | ±1,5 |
| über 120 bis 400 | ±0,2 | ±0,5 | ±1,2 | ±2,5 |
| über 400 bis 1000 | ±0,3 | ±0,8 | ±2 | ±4 |
| über 1000 bis 2000 | ±0,5 | ±1,2 | ±3 | ±6 |
| über 2000 bis 4000 | – | ±2 | ±4 | ±8 |

Tabelle 2, gebrochene Kanten (Rundungshalbmesser, Fasenhöhen, mm) – **B** (Wevolver vollständig, amesweb teilweise übereinstimmend): 0,5 bis 3: f/m ±0,2, c/v ±0,4. Über 3 bis 6: ±0,5 bzw. ±1. Über 6: ±1 bzw. ±2.

Tabelle 3, Winkel nach Länge des kürzeren Schenkels – **B** (Wevolver): Winkeltoleranzen begrenzen nur die Richtung, nicht die Form.

| kürzerer Schenkel (mm) | f und m | c | v |
|---|---|---|---|
| bis 10 | ±1° | ±1°30′ | ±3° |
| über 10 bis 50 | ±0°30′ | ±1° | ±2° |
| über 50 bis 120 | ±0°20′ | ±0°30′ | ±1° |
| über 120 bis 400 | ±0°10′ | ±0°15′ | ±0°30′ |
| über 400 | ±0°5′ | ±0°10′ | ±0°20′ |

ISO 2768-2:1989 H/K/L, zurückgezogen, nur für Bestandszeichnungen – **B** (nur Wevolver):
- Geradheit/Ebenheit für Nennlängen bis 10 / >10–30 / >30–100 / >100–300 / >300–1000 / >1000–3000 mm: H 0,02/0,05/0,1/0,2/0,3/0,4; K 0,05/0,1/0,2/0,4/0,6/0,8; L 0,1/0,2/0,4/0,8/1,2/1,6.
- Rechtwinkligkeit (kürzerer Schenkel bis 100 / >100–300 / >300–1000 / >1000–3000): H 0,2/0,3/0,4/0,5; K 0,4/0,6/0,8/1; L 0,6/1/1,5/2.
- Symmetrie: H 0,5; K 0,6/0,6/0,8/1; L 0,6/1/1,5/2.
- Lauf: H 0,1; K 0,2; L 0,5.

**Widersprüche:**
- Ein Suchauszug der TUM-PDF nannte Kantenstufen bis „über 120 bis 400 ±4“ (vermutlich alte DIN 7168 oder Extraktionsfehler). Ein weiterer nannte „±0,2 für alle Klassen“. Beide sind nicht übernommen.
- DIN Media nennt DIN 2769 „Nachfolger“ der DIN ISO 2768, din.de führt DIN ISO 2768-1 weiter als aktuell.
- Die Schriftfeld-Notation nach ISO 22081 (Form „ISO 22081 – … / A B C“) ist nicht belegt (C).

Toleranzwege für neue Zeichnungen (Folgerung Notiz 03, zur Entscheidung, Kap. Offene Fragen):
1. **Konservativ:** datierte ISO 2768-1 („ISO 2768-m“, ohne K), funktionsrelevante Form- und Lagetoleranzen explizit eintragen.
2. **GPS-konform:** ISO 22081 mit Flächenprofil auf ein vollständiges Bezugssystem, Werte aus DIN 2769.
3. **Übergang:** wie 1, ISO 22081 erst, wenn swki Bezugssysteme ableiten kann.

Die Klasse m (±0,1 bis 6 mm, ±0,2 bis 30, ±0,3 bis 120) gilt als für Standard-CNC mühelos haltbar (C, Folgerung).

### Tolerierungsgrundsatz (ISO 8015, ISO 14405-1)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Unabhängigkeitsprinzip ist Standard | DIN 7167 (Hülle ohne Eintrag) im April 2011 zurückgezogen; EN ISO 14405 macht EN ISO 8015 zum Standard | [Wikipedia DE Allgemeintoleranz](https://de.wikipedia.org/wiki/Allgemeintoleranz); [DIN Media DIN 7167](https://www.dinmedia.de/de/norm/din-7167/1333468) | A | ja – Z (Vermerk vorhanden?) |
| Hülle am Einzelmaß | Ⓔ hinter der Maßtoleranz (Zylinder, zwei parallele Ebenen) oder Normverweis | [Hansgrohe-Anweisung 2020](https://assets.hansgrohe.com/celum/web/Anweisung-zur-Ermittlung-von-Messdaten_2020.pdf) (Suchauszug) | B | nein – bräuchte Passmaß-/Hüllkennzeichen in S |
| Hülle pauschal | „Size ISO 14405 Ⓔ“ über dem Schriftfeld; bei Allgemeintoleranzen „ISO 2768 – mK – E“ (Ausgabe nicht genannt) | Wikipedia DE Allgemeintoleranz | B | ja – Z |
| Bestandszeichnungen vor 2011 ohne Vermerk | in DE galt Hüllprinzip (DIN 7167) | [cad.de Tolerierungsgrundsätze](https://ww3.cad.de/foren/ubb/uploads/Dieter+Fischer/Tolerierungsgrundsaetze.pdf) (Suchauszug, veralteter Stand) | B | – (Bestand: Erstelldatum beachten) |
| Vermerk „Tolerierung ISO 8015“ im Schriftfeld zur Klarstellung; Ⓔ gezielt an Passmaßen statt pauschal; Aufrufprinzip von ISO 8015 | – | – | C, unbelegt | – |

### Passungen (ISO 286)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Einheitsbohrung, Grundzuordnung | H7/g6 Führung, H7/k6 Naben (Gummihammer), H7/p6 Presspassung | [TU Darmstadt](https://www.iim.maschinenbau.tu-darmstadt.de/CAD-Tutorial/CAD-Norminfo/3_important_standards_and_data_sheets/3_tolerances_and_fits/1_selection_and_calculation_of_fits/index.en.html); [Wikipedia Engineering fit](https://wikipedia.com/wiki/Slip_fit); [Hubs](https://www.hubs.com/knowledge-base/understandings-clearance-transition-and-interference-fit/) (Suchauszüge) | A | nein – bräuchte Passungsfeld in S |
| Anwendung (TU Darmstadt) | H7/s6, r6 Presssitz ohne Verdrehsicherung; H7/n6 hoher Fügedruck; H7/m6 Lösen mit Hammer; H7/k6 geringe Kraft; H7/j6 von Hand geschmiert; H7/h6 verschiebbar; H7/g6 kleines Spiel; H7/f7, H8/f7 Gleitlager | TU Darmstadt | B | – |
| Grenzabmaße (µm) | Tabelle unten | [simplybearings](https://simplybearings.co.uk/shop/Info-Pages-ISO-Limits/c4746_4779/index.html) | B | ja – Z (`IDimensionTolerance.GetHoleFitValue`/`GetShaftFitValue`) |
| Wälzlagersitze | Welle IT6, Gehäuse IT7; kleine Lager IT5/IT6; Umfangslast Außenring J7 statt H7; Rundheit Welle IT3–IT4, Gehäuse IT4–IT5 (Klassen 0, 6) | Suchauszüge SKF-Kopien; [JTEKT](https://www.jtekt.co.jp/products/bearing/en/support/bearing-knowledge/14-1000.html) | B | – |
| Eintrag „Ø20 H7“, Grenzabmaße in Klammern „Ø20 H7 (+0,021/0)“; Stiftbohrung H7 für m6-Stift | – | – | C, unbelegt | teilweise – S (`normbohrung art: stift` kennt die Stiftbohrung) |

| Toleranzklasse | über 10 bis 18 | über 18 bis 30 | über 30 bis 50 |
|---|---|---|---|
| H7 | +18 / 0 | +21 / 0 | +25 / 0 |
| g6 | −6 / −17 | −7 / −20 | −9 / −25 |
| h6 | 0 / −11 | 0 / −13 | 0 / −16 |
| k6 | +12 / +1 | +15 / +2 | +18 / +2 |
| m6 | +18 / +7 | +21 / +8 | +25 / +9 |
| n6 | +23 / +12 | +28 / +15 | +33 / +17 |
| p6 | +29 / +18 | +35 / +22 | +42 / +26 |
| r6 | +34 / +23 | +41 / +28 | +50 / +34 |

Beispiele (aus der Tabelle gerechnet): Ø20 H7/g6 Spiel 7 … 41 µm, H7/k6 Übermaß 15 bis Spiel 19 µm, H7/p6 Übermaß 1 … 35 µm.

**Widersprüche:**
- Das Darmstädter Rechenbeispiel Ø7 H7/f7 („f7: −12/−28 µm“, „Mindestspiel 13 µm“) ist in sich widersprüchlich. ISO 286 gibt für f7 >6–10 −13/−28 an. Das Beispiel ist nicht übernommen.
- H7/n6 wird als Übergangs- und als „feste“ Passung eingeordnet.

### Form- und Lagetoleranzen, Bezüge (ISO 1101, ISO 5459, ISO 2692)

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Toleranzrahmen | Felder von links: Symbol, ggf. Ø, Wert in mm, Modifikatoren (MMR, LMR, CZ …), Bezüge in Prioritätsfolge links → rechts | [Keyence](https://www.keyence.de/ss/products/measure-sys/gd-and-t/basic/tolerance-entry-frame.jsp) | B | ja – Z (`IGtolFrame.GetSymbolXml`) |
| Position statt ±-Koordinaten für Bohrbilder | ±-Koordinaten → quadratische Zone; Position Ø t Ⓜ → Kreiszone, Bonustoleranz; TED-Bemaßung ersetzt Koordinatenbemaßung | [americanbobcat](https://americanbobcat.blog/2021/12/01/mechanical-design-engineering-geometrical-dimensioning-and-tolerancing_what-is-the-position-tolerance); [gdandtbasics](https://app.gdandtbasics.com/symbol/true-position) (Suchauszüge) | B | ja – Z (Prüfregel „Bohrbild mit ±-Koordinaten statt Position“); bräuchte Funktionskennzeichen in S |
| ISO 2692:2021 | MMR/LMR nur für Größenmaßelemente Typ Zylinder oder zwei parallele Ebenen | [EVS](https://www.evs.ee/en/evs-en-iso-2692-2021) (Suchauszug) | B | – |
| Vorbild Regelsatz | PTC Creo hat einen ISO-1101-Regelsatz für MBD | [PTC](https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/rule_set_2.html) (nicht gelesen) | B | – |
| Bezugssystem | Einzeltoleranz muss alle durch das Bezugssystem einschränkbaren Freiheitsgrade einschränken | [Zeiss-Forum-PDF](https://qualityforum.zeiss.com/migration/images/241_ddddae37f957c16edfa7d5f1a2f8b076.pdf) (Suchauszug) | B | nein – bräuchte S |
| Bezugsdreieck gefüllt oder leer; Regeln Bezugsbuchstaben; Positionstoleranz-Formel (schwimmend t = Bohrungs-Mindest-Ø − Schrauben-Ø); häufige Toleranzen im Maschinenbau (Ebenheit, Rechtwinkligkeit, Position, Lauf); Bezug primär größte Anlagefläche, sekundär Kante/Bohrung, tertiär Verdrehsicherung | – | – | C, unbelegt | teilweise – S (Anlageflächen aus `verknuepfungen` deckungsgleich der Baugruppe) |

Was ISO 5459:2024 gegenüber 2011 ändert, ist nicht recherchiert. Skripte mit „ISO 5459:2011“ sind veraltet.

## 8. Fertigungs- und prüfgerecht bemaßen

Gelesen wurden: TU Dresden „Hinweise für Biegeteile“, Protolabs „Design Guidelines“, Fictiv „9 tips“, Cambridge Network und die clean-invoice-Checkliste. Die deutschen Lehrunterlagen (RUB, TUM, Zeiss, TU Chemnitz) sind PDFs und liegen nur als Suchauszug vor.

### Grundsätze und Bezüge

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Bezugs- statt Kettenbemaßung, jedes Maß einmal | siehe Kap. 4 | Cambridge Network; buffl.co; Fictiv | A | ja – S/Z |
| fertigungsgerecht | wer so bemaßt, muss den Herstellweg kennen; Fertigungsschritte aus der Bemaßung nachvollziehbar | [RUB](https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598368/mod_resource/content/9/Beschreibung%20fertigungsgerechte%20Bema%C3%9Fung_meta_lizenz.pdf) (Suchauszug) | B | P |
| ohne Umrechnung | fertigungsbezogene Maße direkt nutzbar, prüfbezogene direkt prüfbar | [buffl.co](https://buffl.co/community/c/6946dd6ba18ba13579567696) (schwach) | B | teilweise – Z (kein Maß, das erst gerechnet werden muss) |
| Bezüge an Passflächen | Bezugsebenen beginnend mit kritischen Passflächen, Montageabsicht zeigen | [Fictiv Tip 4](https://www.fictiv.com/articles/9-tips-for-better-engineering-drawings-that-save-time-money) | B | teilweise – S (Baugruppe: `deckungsgleich`-Verknüpfungen nennen Anlageflächen); Teil allein bräuchte Funktionsflächen-Feld |
| Bezüge antastbar, gekennzeichnet; Spannung passend zum Bezugsschema; Toleranzaddition über Aufspannungen | – | [mfgrobots](https://www.mfgrobots.com/Article/mfg/it/54233.html) (Suchauszug, schwach) | B | – |
| Frästeil: je Achse (X, Y, Z) eine Maßbezugskante | – | RUB; [RUB Lösungen](https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598372/mod_resource/content/9/Aufgaben%20zum%20Bema%C3%9Fen%20Mittel%20L%C3%B6sungen_meta_lizenz.pdf) (Suchauszüge) | B | ja – S (`bezug` je Achse; Skill: „möglichst **eine** Bezugsecke“) |
| Single Origin | beseitigt Toleranzaddition zwischen nicht benachbarten Merkmalen; Koordinatenbemaßung nach demselben Prinzip | [industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/engineering-drawing-dimensioning-best-practices-guide); [rivcut](https://rivcut.pages.dev/blog/drawing-callouts-guide) (Suchauszüge) | B | ja – S/Z |
| Stufen- und Abstandsmaße oft mehrdeutig (Bezug unklar) | – | [gpslife](https://gpslife.de/en/?p=1036) (Suchauszug) | B | – |
| Funktionsmaße haben Vorrang; bei Umbemaßung Kette → Bezug Toleranzen so einengen, dass das Funktionsmaß im Worst Case hält; Funktionsabstände (Passbohrungen) direkt eintragen | – | – | C, unbelegt | nein – bräuchte Funktionskennzeichen in S |
| Symmetriebemaßung, wenn funktional zentriert (Zentrierbund, Mittelbohrung) oder Fertigung von der Mitte antastet; sonst von der Anschlagkante | – | – | C, unbelegt (deckt sich mit Skill-Stil „symmetrische Bilder `mitte`, sonst `rand`“) | ja – S (`bezug: mitte` vs. `rand`) |
| Halbzeug: nicht von Walz-/Rohkanten bemaßen, Rohmaße nicht tolerieren, Halbzeugangabe in Schriftfeld/Stückliste | – | – | C, unbelegt | nein – bräuchte Halbzeug-Feld in S |

### Frästeile

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Bohrmaschine vs. Fräsmaschine, Taschen, Nuten | in RUB-Unterlage behandelt, Inhalt nicht gelesen | RUB (Suchauszug) | B | – |
| Maß an das Merkmal setzen, das es bestimmt; eine Einheit; Hilfsansichten/Schnitte für verdeckte Geometrie | – | [Cambridge Network](https://www.cambridgenetwork.co.uk/index.php/news/art-dimensioning-cad-drawings-cnc-machining-traditional-fraftsmans-approach) | B | teilweise – Z |
| Größenordnung Zerspantoleranz | allgemein ±0,1 mm, erreichbar ±0,05, Bohrungen ±0,02 (Werbetext) | Cambridge Network | B, schwach | – |
| je Aufspannung gruppieren, in der Ansicht der Bearbeitungsrichtung bemaßen; Lochbild-Lage vom Bezug, Teilung innerhalb als Funktionsmaß; zentrale Passbohrung als Bezug; Tasche: Breite, Länge, Tiefe von der Einstichfläche, Eckradius als Maß, Lage über Kante/Mitte, nicht über Radiusmittelpunkt; keine Maße zu Mitten unbearbeiteter Merkmale, Tangentenkanten, virtuellen Schnittpunkten | – | – | C, unbelegt | teilweise – S/M (Tasche: `schnitt` + `rechteck` mit `bezug`; Eckradius als `verrundung`, R ≥ T/5 prüfbar) |

### Drehteile

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Wellenabsätze | von den Stirnflächen bis zum größten Ø bemaßen; jeden Absatz-Ø einzeln | RUB (Suchauszug) | B | teilweise – S (`rotation`-Kontur) |
| Freistich | nur mit Normbezeichnung, nicht ausbemaßt, z. B. „DIN 509 – E 0,8 × 0,3“ bzw. „DIN 509 – F 0,6 × 0,3“; in der Vorderansicht nicht gezeichnet; ohne Angabe Rauheit 3,2 µm; Gewindefreistiche DIN 76-1 bis -3 | [Wikipedia Freistich](https://de.wikipedia.org/wiki/Freistich); [TU Chemnitz Abtriebswelle](https://tu-chemnitz.de/mb/mp/lehre/cae/creo/tutorials/data/CAD_AK/03_Abtriebswelle_Creo3_einteilig.pdf) (Suchauszug) | A | nein – bräuchte Freistich als Feature-Typ in S |
| Zentrierbohrungen | vereinfacht nach DIN ISO 6411 | [DIN Media](https://6sku3uaup9f9.din.de/en/standard/din-iso-6411/3044538) | B | nein |
| Passfedernut | Breite P9, N9 oder JS9 (DIN 6885 / DIN 7155), Passfeder h | [Wikipedia Passfeder](https://de.wikipedia.org/wiki/Passfeder) | B | nein |
| Nuttiefe | t1 Welle, t2 Nabe; Zeichnung d − t1 bzw. d + t2 | Suchauszüge (HAW Hamburg, Scribd) | B, schwach | – |
| Ø immer als Durchmesser, nie Radius; Längen von einer Bezugsplanfläche je Aufspannung, verbunden durch Gesamtmaß; Funktionslängen direkt; Zentrierbohrung „ISO 6411-A 2,5/5,3“; Nuttiefe als Restmaß d − t1 (Bügelmessschraube) | – | – | C, unbelegt | teilweise – S (`rotation`) |

### Blechteile

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| Fertigteil | Biegungen als Außenmaße; bei Winkeln ≠ 90° parallel/rechtwinklig zur größten Auflagefläche | [TU Dresden Biegeteile](https://tu-dresden.de/ing/elektrotechnik/die-fakultaet/fakultaetswerkstatt/werkstattteil-praezisionsmechanik/hinweise-fuer-biegeteile) | B | nein – swki hat keine Blech-Features |
| Abwicklung | Blechdicke; zwei Nachkommastellen; von der größten parallelen Seite; gestreckte Länge; alle Biegemittellinien mit Radius, Winkel, Biegerichtung; Lagehinweis | TU Dresden | B | nein |
| Biegeradius | R ≥ Blechdicke | TU Dresden („> s“, bevorzugt R1, R2, R5); [cad.de Blech](https://ww3.cad.de/foren/ubb/uploads/user/Blechkonstruktionen[1].pdf) (Suchauszug) | A | nein |
| Mindestschenkel | 4 × s (Protolabs) bzw. 10 mm (TU Dresden, werkstattspezifisch) | [Protolabs](https://protolabs.com/services/sheet-metal-fabrication/design-guidelines); TU Dresden | B (Widerspruch) | nein |
| Abstand Merkmal–Biegung | ≥ ca. 4 × s | Protolabs | B | nein |
| Loch | Ø ≥ s; Randabstand ≥ 1,574 mm (s ≤ 0,914 mm) bzw. ≥ 3,175 mm | Protolabs | B | nein |
| Biegewinkel | ±1°; möglichst ein Radius für alle Biegungen | Protolabs | B | nein |
| Lineartoleranzen (s < bzw. > 0,13 in) | Kante/Loch zu Kante/Loch 0,13/0,38 mm; Biegung–Loch 0,38/0,635; Biegung–Kante 0,25/0,508; Biegung–Biegung 0,38/0,635; über 3+ Biegungen 0,76/1,016 | Protolabs | B | nein |
| Konstruktion | U-Profil-Schenkel kürzer als ihr Abstand; Ecken/Ausschnitte R ≥ s; Ausschnitt ≥ 1 mm; Senkungen vollständig im Bauteil, bei 90° Kerndurchmesser (Senk-Ø − 2 × s) angeben; Gewindekernlöcher nur ankörnen | TU Dresden | B | nein |
| Abwicklung berücksichtigt Verkürzung; jeder Biegung ein Radius | – | [handwerk-technik](https://www.handwerk-technik.de/_files_media/probeseiten/3208_02.pdf) (Suchauszug) | B | nein |
| Abwicklung nur auf Wunsch des Fertigers (Zuschnitt meist aus DXF), dann als Hilfsmaße; Hinweis „Abwicklung nach Biegetabelle des Fertigers“ | – | – | C, unbelegt | – |

**Widersprüche:**
- Mindestschenkel: 10 mm fest (TU Dresden) vs. 4 × s (Protolabs).
- Lochabstand zur Biegung: ≈ 4 × s (Protolabs) vs. 2,5 × s + Innenradius (Drittanbieter, nur Auszug, nicht belastbar).
- Biegeradius: „> s“ (TU Dresden) vs. feste Werkzeugradien 0,762/1,524/2,286/3,048 mm (Protolabs).

### Was der Fertiger braucht, was stört, typische Fehler

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| keine Überbemaßung | – | TUM (Suchauszug); buffl.co; Fictiv Tip 7 | A | ja – Z |
| keine unnötig engen Toleranzen | „verteuert die Fertigung massiv“; nur funktionskritische Merkmale tolerieren | [clean-invoice](https://www.clean-invoice.com/feinwerkmechanik/checkliste-feinwerkmechanik); Fictiv | A | teilweise – Z (Anteil einzeltolerierter Maße); bräuchte Funktionskennzeichen in S |
| Pflichtinhalt | alle Maße, Toleranzen, Oberflächen (Ra), Werkstoff; Fehler: kein 3D-Modell, Material fehlt, keine Erstmusterfreigabe bei Serie | clean-invoice | B | teilweise – S (`material`) + Z |
| Allgemeintoleranz für Maße ohne Einzeltoleranz | – | buffl.co | B | ja – Z |
| Zukauf-/Normteile | Hersteller + Bestellnummer bzw. vollständige Normbezeichnung; Gewinde mit Norm; Nebendokumente an einer Stelle | Fictiv Tips 2, 5, 6 | B | ja – S (`quelle: normteil`/`kaufteil`) |
| Lesbarkeit | gedrängte Maße und mehrdeutige Platzierung führen zu Fehlablesung; vor Freigabe prüfen | Cambridge Network | B | ja – Z (Text-Überlappung) + P |
| Lohnfertiger kennt Funktion nicht | Bitte „Fehler finden“ hilft nicht | [woodworker.de Forum](https://www.woodworker.de/forum/goto/post?id=621915) (schwach) | B | – |
| typische Störungen | Maße an verdeckten Kanten, zu Tangentenkanten oder theoretischen Schnittpunkten, Maße, die erst gerechnet werden müssen, doppelte Maße, gemischte Einheiten, Dezimalpunkt statt Komma, ungeordnete CAD-Autobemaßung (Skizzenmaße 1:1 übernommen) | – | C, unbelegt | ja – Z (`GetAttachedEntities3`, Sichtbarkeit, Maßgraph) |

**Widerspruch:**
- Fictiv (US, modellbasiert): Maße kommen aus dem 3D-Modell, die Zeichnung trägt nur Gewinde und kritische Prüfmaße.
- Deutsche Lehre und Checkliste: vollständig bemaßte, DIN-gerechte Zeichnung, jedes Maß einmal.
- Beide nennen das 3D-Modell als Beilage.

### Prüfgerecht

| Regel | Wert/Bedingung | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| „Design with measurement in mind“ | für jedes Maß das Prüfmittel bedenken (Handmessmittel oder KMG); Prüftiefe nach Entwicklungsstufe; GD&T und Rauheit brauchen ggf. aufwendige Prüfung | Fictiv Tips 8–9 | B | P |
| nur montagekritische und messbare Maße | – | Fictiv | B | – |
| kein Maß zum virtuellen scharfen Eck ohne Hinweis; keine Lagemaße zu nicht antastbaren Mitten; Tiefen von zugänglicher Fläche; Prüfmaß-Kennzeichnung (Rahmen mit runden Enden) | – | – | C, unbelegt | ja – Z (`GetAttachedEntities3`) |

### Abgleich mit dem Hausstil

| Hausregel | Folge für die Zeichnung | prüfbar durch swki |
|---|---|---|
| Fasen nur an Bohrungseintritten 0,5 × 45° | Fase an der Bohrungsangabe mitschreiben (Folgerung Notiz 05, C), nicht als eigenes Lagemaß; Außenkanten über die ISO-13715-Sammelangabe | ja – S (`fase`) gegen Z |
| Innenradien R ≥ Tiefe/5 | Eckradius als Maß an der Tasche; Prüfregel R ≥ T/5 | ja – S/M |
| Halbzeug statt aus dem Vollen | Halbzeugangabe in Schriftfeld/Stückliste, Rohkanten nicht bemaßen und tolerieren (C) | nein – bräuchte Halbzeug-Feld in S |
| Muster nur für Reihen ≥ 3 | Zeichnung schreibt die Anzahl unabhängig davon („n ×“); Teilung als Funktionsmaß | ja – S (`muster_linear`, `positionen`) |
| eine Bezugsecke, `bezug` je Lage | direkt Basis der Zeichnungsbemaßung (Parallel- bzw. Koordinatenbemaßung) | ja – S |

## 9. Baugruppenzeichnung, Positionsnummern (ISO 6433), Stückliste (ISO 7573)

### Positionsnummern (ISO 6433:2012)

Die Normsätze stammen nur aus Suchauszügen der Vorschau-PDFs („laut Suchauszug“), sind also höchstens B. A entsteht nur, wo eine zweite Quelle bzw. die Ausgabe 1981 (RoyMech) übereinstimmt.

| ID | Regel | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| POS-01 | Positionsnummer außerhalb der Teilumrisse, mit Hinweislinie zum Teil | [iTeh EN ISO 6433:2012](https://standards.iteh.ai/catalog/standards/cen/b35bb0cd-5f83-46b2-9c85-ef0a7848124f/en-iso-6433-2012) (Suchauszug); [RoyMech](https://www.roymech.co.uk/Useful_Tables/Drawing/Item_Ref.html) (1981) | A | ja – Z (Ballon-Hüllrechteck gegen Silhouette aus `GetPolylines7`) |
| POS-02 | jede Positionsnummer über Hinweislinie verbunden | [TUD Explosionszeichnung](https://www.iim.maschinenbau.tu-darmstadt.de/kursunterlagen/plcm_tutorials/CAD/TPD/Explosionszeichnung/); [technisches-zeichnen.net](https://www.technisches-zeichnen.net/technisches-zeichnen/grundkurs-02/gruppenzeichnungen-positionsnummern.php) | A | ja – Z (`IsDangling`, `GetAttachedEntities3`) |
| POS-03 | Hinweislinien kreuzen sich nicht | [iTeh SIST EN ISO 6433](https://standards.iteh.ai/catalog/standards/sist/d1b5a81a-3542-445d-94f7-e25a9ecf7543/sist-en-iso-6433-2012) (Suchauszug); [maschinenbau-wissen.de](https://www.maschinenbau-wissen.de/skript3/konstrkution-entwicklung/technisches-zeichnen/171-positionsnummern); [TUD cad_ss16](https://www.iim.maschinenbau.tu-darmstadt.de/kursunterlagen_archiv/cad_ss16/732_explosionsdarstellung_mit_stckliste_und_positionsnummern_anpassen.html) | A | ja – Z (Segmentschnitt paarweise) |
| POS-04 | Hinweislinien so kurz wie möglich (A); sollen keine anderen Bauteile schneiden (B, nur TUD) | TUD cad_ss16; maschinenbau-wissen.de | A/B | ja – Z (als Warnung: Teile im Schnittinneren erzwingen Kreuzung) |
| POS-05 | Linienende nach ISO 128-22: Punkt (Ø ≈ 5 × Linienbreite) in der Fläche, Pfeil auf Kante, ohne Abschluss auf Maß-/Symmetrielinie | [iTeh ISO 128-22](https://standards.iteh.ai/catalog/standards/iso/225fb29c-8da9-432d-a5b9-9cfc021ac313/iso-128-22-1999) (Suchauszug); [CAD Setter Out](https://cadsetterout.com/drawing-standards/technical-drawing-standards-leader-lines/) | A (Regel); Gültigkeit ISO 128-22 s. Kap. 1 | ja – Z (Ankertyp aus `GetAttachedEntityTypes`) |
| POS-06 | Nummer darf im Kreis aus schmaler Volllinie stehen (A); Hinweislinie zielt dann auf den Kreismittelpunkt (B); Kreisdurchmesser nicht gefunden | iTeh SIST (Suchauszug); technisches-zeichnen.net | A/B | ja – Z |
| POS-07 | alle Positionsnummern gleiche Art und Schrifthöhe | iTeh EN (Suchauszug) | B | ja – Z |
| POS-08 | von anderen Angaben unterscheidbar (A); größere Schrifthöhe nur als Bild-Variante (B); „2 × Maßzahlhöhe“ unbelegt (C) | iTeh SIST (Suchauszug); RoyMech | A/B/C | Hausregel – Z |
| POS-09 | möglichst in waagerechten Reihen bzw. senkrechten Spalten („should“) | iTeh (Suchauszug); TUD; maschinenbau-wissen.de; RoyMech | A | ja – Z (Ballonmittelpunkte auf gemeinsamer x/y-Linie) |
| POS-10 | gleiche Teile gleiche Nummer, möglichst nur einmal angetragen | iTeh (Suchauszug); TUD; technisches-zeichnen.net; RoyMech | A | ja – S (Teiltyp = `quelle` + Variante) + Z |
| POS-11 | jede Unterbaugruppe eigene Nummer | technisches-zeichnen.net; RoyMech | A | ja – S |
| POS-12 | gemeinsame Hinweislinie für mehrere Nummern zulässig (A; typisch Schraube + Scheibe + Mutter); Stückzahl an der Nummer (Anhang A, B); Trennung durch Bindestrich, Schrägstrich, Komma (B, Suchauszug) | iTeh EN (Suchauszug); RoyMech; Europa-Lehrmittel (Suchauszug) | A/B | teilweise – S (`je_position`: Normteile je Bohrung; Zusammengehörigkeit Schraube + Scheibe + Mutter bräuchte Ableitung oder Spec-Feld) → Stapelpositionsnummer |
| POS-13 | Reihenfolge nach Zusammenbau oder im Uhrzeigersinn; keine Normpflicht gefunden | maschinenbau-wissen.de; Europa-Lehrmittel (Suchauszug) | B | Hausregel |
| POS-14 | Winkel der Hinweislinie: > 15° zu Hauptlinien und Blattrand, nicht parallel zu Schraffur (TUD) vs. „beliebig, nicht waagerecht/senkrecht“ (TUD) vs. 15°-Schritte (CAD Setter Out) | TUD; CAD Setter Out | B (Widerspruch) | Hausregel – Z |
| POS-15 | Positionsnummer = Zahl, ggf. mit Großbuchstaben (1981); 2012 neue Anmerkung zu 4.1 „Identifikatoren“, Inhalt unbekannt | RoyMech | B | – |

**Widerspruch POS-05:**
- Die Lehrseiten erlauben Pfeil oder Punkt frei.
- TUD verlangt Pfeile auf der äußeren Berandungslinie.
- Mit ISO 128-22 vereinbar ist: Pfeil, wenn die Spitze auf einer Kante sitzt; Punkt in der Fläche.

### Stückliste (ISO 7573:2008)

| ID | Regel | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| STL-01 | Mindestanforderungen für manuelle und rechnererzeugte Stücklisten | [iTeh SIST ISO 7573](https://standards.iteh.ai/catalog/standards/sist/bbd903b9-abf9-44d0-a828-9dd6e0d56f56/sist-iso-7573-2010) (Suchauszug) | B | – |
| STL-02 | alle Datenfelder optional, mindestens ein identifizierendes Element; Firmen dürfen Felder ergänzen | ebd. | B | ja – Z (`GetComponents2`, Zeileninhalt) |
| STL-03 | Identifikation über Sachnummer und/oder „technische Daten, Benennung“ | ebd. | B | ja – S |
| STL-04 | Menge = Stückzahl oder Materialmenge; Spalte „Einheit“ nicht gefunden (DIN 6771-2 Form A: Position, Menge, Einheit, Benennung, Sachnummer, Bemerkung) | ebd.; [Streit Software](https://www.streit-software.de/vorlagen/stueckliste-vorlage) | B | ja – S (Instanzzahl aus `komponenten`/`je_position`) |
| STL-05 | Referenzkennzeichen = je Vorkommen, Positionsnummer = je Teiltyp | ebd. | B | – |
| STL-06 | 1983: Spalten Item, Description, Quantity, Reference, Material; Menge je fertige Baugruppe; Reference = Zeichnung, Kaufteil, Code | Suchauszug 1983; RoyMech | A (nur 1983) | – |
| STL-07 | Spaltenfolge frei | Suchauszug 2008/1983; RoyMech | A | – |
| STL-08 | Stückliste auf der Zeichnung oder als eigenes Dokument | Suchauszug; RoyMech | A | – |
| STL-09 | Leserichtung wie Schriftfeld; bei Kombination mit Schriftfeld Kopf „in direct …“ (Satz abgeschnitten) | Suchauszug 2008 | B | ja – V |
| STL-10 | auf der Zeichnung von unten nach oben, Kopf am Schriftfeld | Suchauszug 1983; TUD (nach DIN 6771-2) | A für alte Normen/Praxis, für 2008 C | Hausregel – V |
| STL-11 | Sortierung: Eisen, NE-Metalle, Nichtmetalle, dann Norm- und Zukaufteile; gleichartige Normteile hintereinander | TUD | B (Hausregel) | Hausregel – S |
| STL-12 | Normteile mit Normbezeichnung als „Normteil“; Benennung „Bolt – Size – Grade“ mit Normnummer; DIN 912 zurückgezogen, ISO 4762 verwenden | WKO-OÖ (Suchauszug); RoyMech; [Böllhoff](https://eshop-pl.boellhoff.com/en/Screws/Screws-with-internal-force-application/Cylinder-screws/Cylinder-screws-/-17.html) | B | ja – S (`quelle: normteil` „Norm Größe“) |
| STL-13 | Halbzeug und Normteil als Begriffe; Pflichtspalten Hersteller/Bestellnummer nicht gefunden | Wiley Register (Suchauszug) | C | ja – S (`quelle: kaufteil` „Hersteller Bestellnummer“, Katalogeintrag) |
| – | Format „Zylinderschraube ISO 4762 – M8 × 25 – 8.8“ (Bezeichnungsbeispiel der Produktnormen) | – | C, unbelegt | ja – S |

### Inhalt der Baugruppenzeichnung und Zeichnungssatz

| ID | Regel | Quelle | Beleg | prüfbar durch swki |
|---|---|---|---|---|
| BG-01 | Teile und Normteile im zusammengebauten Zustand, mit Positionsnummern und Stückliste | technisches-zeichnen.net; Europa-Lehrmittel (Suchauszug) | A (Lehrpraxis) | ja – Z |
| BG-02 | meist Vollschnitt; oft Montagevorlage | Frankfurt UAS (Suchauszug) | B/C | P |
| BG-03 | volle Teile (Wellen, Bolzen, Niete, Stifte, Schrauben, Passfedern, Keile, Wälzkörper, Gussrippen) nicht längs schneiden; Schraffur nicht versetzen | TUM (Suchauszug); vgl. Kap. 3 | B | teilweise – S (Normteile, Kaufteile); Wellen bräuchte Spec-Kennzeichen; Z (`IDrSection.GetExcludedComponents`) |
| BG-04 | Schraffur 45°/135°, Abstände je Bauteil; ISO 128-3 hat Abschnitte „Schraffur“ und „C.4 Angrenzende Teile“ | TU Chemnitz (Suchauszug, C); DIN Media (Gliederung, B) | C/B | ja – Z (`GetFaceHatches` je Komponente) |
| BG-05 | Endlagen beweglicher Teile als schmale Strich-Zweipunktlinie (05.1) | Hintergrundwissen; Linienart 05 im DIN-TOC (Suchauszug) | C | teilweise – S (`bewegungen`, Grenzverknüpfung `min`/`max`) |
| BG-06 | welche Maße auf die Baugruppenzeichnung gehören (Haupt-, Anschluss-, Einbau-, Hubmaße, Passungen an Fügestellen) | Hoischen-TOC (Suchauszug) | C | teilweise – S (`pruefung.huellquader`, `bewegungen`) |
| SATZ-02 | Stücklistenarten: Struktur (alle Stufen), Baukasten (eine Ebene, Unterbaugruppen eigene Liste), Mengenübersicht (aufgelöst, ohne Baugruppen) | [Wikipedia DE Stückliste](https://de.wikipedia.org/wiki/St%C3%BCckliste) | B | ja – S (eine Baugruppen-Spec = eine Stufe) |
| SATZ-04 | Stückliste verweist auf Einzelteilzeichnung, Kaufteil, Code; Normteile ohne eigene Zeichnung (gefolgert) | RoyMech | B/C | ja – S |
| SATZ-05 | Explosionsdarstellung: Teile entlang einer Achse verschoben; mehrere Pfeile von einer Nummer für gleiche Teile zulässig; keine Norm gefunden | [TUD Explosionszeichnung](https://www.iim.maschinenbau.tu-darmstadt.de/kursunterlagen/plcm_tutorials/CAD/TPD/Explosionszeichnung/); [Wikipedia DE Explosionszeichnung](https://de.wikipedia.org/wiki/Explosionszeichnung) | B | – |
| SATZ-06 | Revisionsindex s. Kap. 2; Platz einer Änderungstabelle: keine Quelle | – | C | – |
| SATZ-07 | SolidWorks: erste Komponente Pos. 1 (vorlagenabhängig); Nummern sequenziell ordnen, Stückliste folgt; Stapelpositionsnummer als eigener Typ | [SW-Hilfe Numbering Balloons](https://help.solidworks.com/2016/English/SolidWorks/Sldworks/t_Numbering_Balloons_Sequentially.htm); [Balloon Styles](https://help.solidworks.com/2017/English/SolidWorks/Sldworks/c_Balloon_Styles_and_Sizes.htm) (Suchauszüge) | B | – |
| – | Anzugsmomente, Klebstoffe, Sicherungsmittel als Zeichnungshinweis | keine Quelle gefunden | C | – |

Folgerungen:
- Die Struktur von swki passt zur Baukastenstückliste: eine Baugruppen-Spec ist eine Stufe.
- Datenquellen für die Spalten:
  - Eigenteile → Dokumentnummer der Einzelteilzeichnung
  - Normteile → Normbezeichnung aus `swki/wissen/normteile/`
  - Kaufteile → Hersteller und Bestellnummer aus `swki/wissen/kaufteile/`
- Prüfbar: Anzahl verschiedener Positionsnummern = Stücklistenzeilen der Stufe, Menge = Instanzen je Teiltyp aus der Spec.
- Ein Spec-Kennzeichen „nicht schneiden“ (z. B. `schnitt: nein`) gibt es nicht. swki bräuchte es für Wellen und Achsen, die keine Norm- oder Kaufteile sind.

## 10. SolidWorks-2025-API für die Ableitung

Quelle aller Zeilen ohne eigenen Link: Offline-Index SW 2025 (`swki api methode …`), Seiten gleichen Namens unter `https://help.solidworks.com/2025/english/api/sldworksapi/…` bzw. `…/swconst/…`. Angaben: n = Parameterzahl laut Index, „seit“ = Verfügbarkeit laut Index.

Spalte „Art“:
- **frei** = ohne Vorauswahl aufrufbar
- **Auswahl** = braucht vorher ausgewählte Ansicht, Entität oder Markierung
- **Dialog** = verlangt Nutzereingriff
- **fehlt** = nicht im Index bzw. nicht vorhanden

### Zeichnung anlegen

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Zeichnung aus Vorlage | `ISldWorks.NewDocument(TemplateName, PaperSize, Width, Height)` (4, 2000); Standardvorlage über `GetUserPreferenceStringValue(swDefaultTemplateDrawing=10)` | Pfade für Blattformate `swFileLocationsSheetFormat=7`, Normdateien `=64` | A ([Hilfe-Beispiel Insert Model Annotations](https://help.solidworks.com/2025/english/api/sldworksapi/Insert_Model_Annotations_Example_CSharp.htm)) | frei |
| Blatt, Format, Maßstab, 1. Winkel | `IDrawingDoc.SetupSheet6` (17, 2015; ersetzt SetupSheet5); `NewSheet4` (16, 2015); `ISheet.SetProperties2` (8, 2016) / `GetProperties2` (8 Doubles) | danach `ForceRebuild3`, damit die Projektionsart in den Ansichten ankommt; eigenes Format per `SetTemplateName` nach `swDwgTemplateCustom` | B | frei |
| Papiergrößen | `swDwgPaperSizes_e`: A4size=6, A4sizeVertical=7, A3=8, A2=9, A1=10, A0=11, `swDwgPapersUserDefined`=12 | Schreibweise „Papers“ laut Index verbindlich (Hilfetext abweichend) | B | – |
| Zeichnungsnorm | `IModelDocExtension.SetUserPreferenceInteger(swDetailingDimensionStandard=13, …)`, `swDetailingStandard_e`: ANSI=1, ISO=2, DIN=3 …; `LoadDraftingStandard`/`SaveDraftingStandard` (.sldstd) (je 1, 2009) | – | B | frei |
| Einheiten, Genauigkeit | `swUnitSystem=263`, `swUnitsLinear=47`, `swDetailingLinearDimPrecision=24`, `…TolPrecision=25` | – | B | frei |
| Dezimalkomma | nur Systemoption `swUseSystemSeparatorForDims=82` (Anwendung, nicht Dokument) und `swGtolDecimalSeparatorType=625` (nur GTol) | dokumentweiter Schalter für Maße nicht im Index → Komma über Vorlage/.sldstd sichern und zurücklesen | B | fehlt (Dokumentebene) |
| Projektion, Kantenanzeige | `swDrawingProjectionType=79`, `swHiddenEdgeDisplayDefault=76`, `swTangentEdgeDisplayDefault=77` | Verhältnis zu `FirstAngle` in SetupSheet6 nicht belegt | B | frei |

### Ansichten

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| drei Standardansichten | `IDrawingDoc.Create1stAngleViews2(ModelName)` (1, SW 99 SP01) | folgt automatischer Skalierung | B | frei |
| Modellansicht | `CreateDrawViewFromModelView3(ModelName, ViewName, X, Y, Z)` (5, 2005 SP2) | ViewName exakt inkl. Stern („*Front“); deutsche Namen über `IModelDoc2.GetModelViewNames()` ermitteln | B | frei |
| Ansichtenpalette | `GenerateViewPaletteViews`, `DropDrawingViewFromPalette2` (2007 SP4) | – | B | frei |
| Projektionsansicht | `CreateUnfoldedViewAt3(X, Y, Z, NotAligned)` (4, 2005) | Vorauswahl der Elternansicht (C) | B | Auswahl (C) |
| Hilfsansicht | `CreateAuxiliaryViewAt2` (7, 2001) | Vorauswahl einer Kante (C) | B | Auswahl (C) |
| Schnittansicht | `CreateSectionViewAt5(X, Y, Z, Label, Options, ExcludedComponents, Depth)` (7, 2010); Optionen u. a. ExcludeFasteners=64 | **Schnittlinie muss vorher als Skizze gezeichnet und ausgewählt sein**; Bezeichnung über `IView.GetSection` → `IDrSection.SetLabel2` | B | Auswahl |
| Detailansicht | `CreateDetailViewAt4` (12, 2017); `swDetViewStyle_e`, `swDetCircleShowType_e` | Vorauswahl Detailkreis (C) | B | Auswahl (C) |
| Bruchansicht | `IView.InsertBreak3` (6, 2018); `swBreakLineStyle_e` ZigZag=2, SmallZigZag=4 … | – | B | frei |
| Abwicklung Blech | `CreateFlatPatternViewFromModelView3` (7, 2007 SP5) | – | B | frei |
| Darstellung | `IView.SetDisplayMode4` (5, 2021): HIDDEN=2 (verdeckt aus), HIDDEN_GREYED=1; `SetDisplayTangentEdges2` | – | B | frei |
| Maßstab, Lage, Ausrichtung | `IView.ScaleRatio`, `UseSheetScale`, `Position`, `AlignWithView` (2, 2004) | danach `EditRebuild3` | B | frei |
| Platzbedarf | `IView.GetOutline()` (Blattkoordinaten), `GetXform()` (kleines f) | keine API „Ansichten automatisch anordnen“ → selbst rechnen | B | fehlt (Auto-Anordnung) |

### Bemaßung erzeugen

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Modellmaße übernehmen | `IDrawingDoc.InsertModelAnnotations3` (6, 2005), `…4` (8, 2024 FCS); Typen `swInsertAnnotation_e` bitweise: Dimensions=8, **DimensionsMarkedForDrawing=32768**, HoleWizardLocationDimensions=131072, **holeCallout=1048576** (`swInsertholeCallout`), **TolerancedDims=16777216** | wirkt auf ausgewählte Ansicht (AllViews für alle); Foren: nur Option 0 (ganzes Modell) funktionierte zuverlässig (C) | B | Auswahl |
| Annotationen importieren | `IView.ImportAnnotations(Design, CosmeticThreads, DimXpert, HiddenFeatureItems, 3DView)` (5, **2025 FCS**) | ob Baugruppenprobleme von InsertModelAnnotations3 gelöst: unbekannt | B | frei |
| Autobemaßung | `IDrawingDoc.AutoDimension` (5, 2005); `swAutodimScheme_e`: Baseline=1, Ordinate=2, Chain=3, Centerline=4 | Bezüge vorher auswählen und markieren (`swAutodimMark_e`); bemaßt nach Algorithmus, nicht nach Funktion | B | Auswahl |
| manuelle Maße | `IModelDoc2.AddDimension2` u. a. (3, 2001Plus); `IModelDocExtension.AddDimension` (4, 2015); `AddSpecificDimension` (5, 2018, auch Zeichnung, Typen inkl. Chamfer, Ordinate) | Auswahl **nach Lage, nicht nach Name** (sonst Zufallspunkte); `AddRadialDimension2` nur in aktiver Skizze | B | Auswahl |
| Kanten in Ansicht auswählen | `IView.SelectEntity(Entity, Append)` (2001Plus); Lage über `IView.ModelToViewTransform`; sichtbare Entitäten `GetVisibleEntities2` (2, 2014, Silhouettenkanten) | nur `GetVisibleEntities2` berücksichtigt Verdeckung; `GetVisibleComponents` liefert unvollständige Objekte → `GetVisibleDrawingComponents` (2021) | A ([codestack Bemaßen](https://www.codestack.net/solidworks-api/document/drawing/view-dimension-model-entities/); [codestack Auswahl](https://www.codestack.net/solidworks-api/document/selection/drawing-view-entities/)) | Auswahl |
| Koordinatenmaße | `IModelDocExtension.AddOrdinateDimension` (4, 2007) | Basis vorher wählen, weitere danach; `SetPickMode` | B | Auswahl |
| Fasenmaß | `IDrawingDoc.AddChamferDim` (3, 2001Plus) oder `AddSpecificDimension` Chamfer=10 | – | B | Auswahl |
| **Bohrungsangabe** | `IDrawingDoc.AddHoleCallout2` (3, 2001Plus) | **„the user must click OK in the dialog“** → für Automatik ungeeignet; Ersatz über `InsertModelAnnotations` mit `swInsertholeCallout`, ob ohne Dialog: ungeprüft | B | Dialog |
| Bohrungstabelle | `IView.InsertHoleTable3` (9, 2019); Vorlage *.sldholtbt | Auswahl mit Markierung Ursprung=1, Kanten=2, X=4, Y=8 | B | Auswahl |
| Mittelpunktmarken | `IView.AutoInsertCenterMarks2` (10, 2016; je Ansicht nach `ActivateView`); `IDrawingDoc.InsertCenterMark3` (3, 2009) | `IDrawingDoc.AutoInsertCenterMarks2` gibt es nicht | B | frei bzw. Auswahl |
| Mittellinien | nur `IDrawingDoc.InsertCenterLine2()` (0, 2005) mit Auswahl; automatisch nur über Dokumentoption `swDetailingAutoInsertCenterLines` (190) beim Erzeugen | ob die Option bei API-Ansichten greift: ungeprüft | B | Auswahl; Auto-API fehlt |
| Anordnung | `IModelDocExtension.AlignDimensions(AlignType, SpaceValue)` (2, 2011), AutoArrange=0, SpaceEvenly=1 | – | B | Auswahl |
| Toleranz, Passung | `IDimensionTolerance.Type` (`swTolType_e`: BASIC=1, BILAT=2, SYMMETRIC=4, FIT=7, FITWITHTOL=8 …), `SetValues2` (4, 2013 SP04), `SetFitValues(Hole, Shaft)` (2, 2006) | – | B | frei |
| Maßanzeige | `IDisplayDimension.SetPrecision3`, `ShowParenthesis` (Hilfsmaß), `Inspection` (Prüfmaß), `SetText`, `CenterText` | – | B | frei |
| Allgemeintoleranz-Tabelle | `IModelDocExtension.InsertGeneralToleranceTableAnnotation(Template, X, Y)` (3, 2018; X/Y laut Index Integer) | – | B | frei |

### Zurücklesen zur Prüfung

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Ansichten | `ISheet.GetViews()` (2008); `IDrawingDoc.GetFirstView()` liefert zuerst das **Blatt**; `GetSheetNames`, `ActivateSheet` | auf aktivem Blatt auch Standard-/benannte Ansichten | B | frei |
| Maße | `IView.GetDisplayDimensions()` (2009 SP1); `GetFirstDisplayDimension5` ab **2025 SP01** überholt → `GetFirstDisplayDimension6` (auch inaktive Blätter) | liefern auch Blattformat- und unterdrückte Maße | B | frei |
| Annotationen | `IView.GetAnnotations()` (2005), `GetFirstAnnotation3`; Typ `swAnnotationType_e` (DisplayDimension=4, GTol=5, Note=6, SFSymbol=7, CenterMarkSym=13, TableAnnotation=14, CenterLine=15 …); `GetAnnotationsByType` erst **2025 SP02** | auch lose, ausgeblendete Annotationen → mit `Visible` filtern | B | frei |
| Maß ↔ Modell | `IDisplayDimension.GetDimension2`; `IDimension.FullName` („D1@Skizze1@Teil.Part“), `GetSystemValue3` (SI-Einheiten), `DrivenState`, `IsReferenceDim`, `IsHoleCallout` | – | B | frei |
| Anker, lose Maße | `IAnnotation.GetAttachedEntities3` (2008), `GetAttachedEntityTypes`, `IsDangling` (2009) | – | B | frei |
| Lage, Überlappung | `IAnnotation.GetPosition`/`SetPosition2`; `IView.GetDimensionDisplayInfo5` (Linien, Pfeile, Textlagen, Rahmenecken); Notizen: `GetPosition` + `INote.GetUpperRight`/`GetHeight` | **keine** fertige Hüllquader-Methode für Annotationen → selbst rechnen | B | fehlt (Hüllquader) |
| Ansichtsgeometrie | `IView.GetPolylines7` (2, 2008): sichtbare Kanten, auch verdeckte Teile, ohne Topologie | Topologie über `GetVisibleEntities2` | B | frei |

### DimXpert und MBD

| Aufgabe | Methode | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Einstieg | `IModelDocExtension.DimXpertManager(Config, CreateSchema)` (2, 2010), `IDimXpertManager.DimXpertPart` | nur für geöffnete Teile | B | frei |
| Auto-Bemaßungsschema | `IDimXpertPart.AutoDimensionScheme(Option)` | Bibliothek `SolidWorks.Interop.swdimxpert` **fehlt im Offline-Index** → Signaturen unbelegt; Bezüge muss der Nutzer angeben; bemaßt nach Fertigungsmerkmalen, nicht nach Spec | C ([Hilfe 2015](https://help.solidworks.com/2015/English/api/swdimxpertapi/SolidWorks.Interop.swdimxpert~SolidWorks.Interop.swdimxpert.IDimXpertPart~AutoDimensionScheme.html), Suchauszug) | fehlt (Index) |
| Lizenz | DimXpert in jeder Lizenz, MBD separat | [Hawkridge](https://hawkridgesys.com/blog/mbd-dimxpert-and-mbd-dimensions-whats-the-difference); [GoEngineer](https://www.goengineer.com/blog/introduction-dimxpert-solidworks) (Händler) | C | – |
| in die Zeichnung | `ImportAnnotations(…, IncludeDimXpertAnnotations, …)`; PMI über `swPMIOnly` | – | B | frei |

### Annotationen: Form und Lage, Bezüge, Oberflächen, Notizen, Gewinde, Kanten

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Form-/Lagetoleranz | `IModelDoc2.InsertGtol()` (0, 2001Plus; Leitlinie an Vorauswahl); `IGtol.SetFrameValues2` (6, 2016) | seit SW 2022 neues Rahmenformat: `IGtol.GetFrameValues` nur für ältere GTols; neu `IGtol.GetFrame`/`AddFrame`, `IGtolFrame.GetSymbolXml`/`SetSymbolXml` (2023, Schema über `GetGtolFrameXMLSchema`); ob `SetFrameValues2` auf das neue Format wirkt: unbelegt | B | Auswahl |
| Bezüge | `IModelDoc2.InsertDatumTag2()` (0, 2001Plus); `InsertDatumTargetSymbol3` (16, 2018) | – | B | Auswahl |
| Oberflächensymbol | `IModelDocExtension.InsertSurfaceFinishSymbol3` (14, 2005), `swSFSymType_e` | **kein Normparameter**, Felder im Stil ISO 1302; Norm über Dokumentoption `swDetailingSFSymbolStandard=629`, Wert **21920_1=2**; UI-Hilfe: ISO-21920-Symbole ab **2025 SP1** (C) | B (Enum); C ([What's New 2025](https://help.solidworks.com/2025/English/WhatsNew/c_wn2025_drawings_iso_standard_surf_fin_symb.htm), Suchauszug) | frei |
| ISO 21921 in SW 2026 | Händlerankündigung | [Javelin](https://www.javelin-tech.com/3d/drawings-whats-new-in-solidworks-2026/) | C | – |
| Notizen | `IModelDoc2.InsertNote(Text)` (1); `INote.PropertyLinkedText` (ungelöster Text mit `$PRPVIEW` …) | – | B | frei |
| Gewindedarstellung | im Modell `IFeatureManager.InsertCosmeticThread3` (7, 2015); in die Zeichnung `swInsertCThreads=1` bzw. `ImportAnnotations`; `ICosmeticThreadFeatureData.ThreadCallout` | – | B | frei |
| **Kantenzustand ISO 13715** | keine API gefunden | Notiz oder eigener Symbolblock nötig (unbelegt) | B | fehlt |

### Schriftfeld über Eigenschaften

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Eigenschaften setzen/lesen | `IModelDocExtension.CustomPropertyManager(Config)` (`""` = Dokument); `ICustomPropertyManager.Add3` (4, 2014), `Set2` (2, 2014), `Get6` (6, 2018, liefert aufgelösten Wert) | Modell: Benennung, Sachnummer, Werkstoff, Masse; Zeichnung: Revision, Datum, Freigabe (Folgerung) | B | frei |
| Quelle der Modelleigenschaften | `ISheet.CustomPropertyView` bzw. `PropertyViewName` in SetupSheet6 | – | B | frei |
| Schriftfeldnotizen | `ISheet.TitleBlock` → `ITitleBlock.GetNotes()` (2009); Format bearbeiten `EditTemplate` ↔ `EditSheet2` (**2024 SP02**), `ReloadTemplate`, `SaveFormat` | `GetEditableNotes` nicht im Index | B | frei |
| `$PRP` vs. `$PRPSHEET` | Syntax belegt, Abgrenzung widersprüchlich; `SW-Sheet Scale` zeigt den Blatt-, nicht den Ansichtsmaßstab | [SW-Hilfe 2022](https://help.solidworks.com/2022/english/solidworks/sldworks/t_link_notes_to_document_properties.htm); [CADimensions](https://knowledge.cadimensions.com/knowledge/what-are-drawing-property-links); [Forum](https://forum.solidworks.com/thread/98928) | C | – |

### Baugruppe: Stückliste, Positionsnummern, Schnitt, Schraffur

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Stückliste | `IView.InsertBomTable6` (12, **2025 FCS**); `swBomType_e`: PartsOnly=1, TopLevelOnly=2, Indented=3, Flattened=4; Vorlage .sldbomtbt | bei TopLevelOnly keine Configuration angeben; ungültige Configuration → keine Stückliste | B | frei |
| Stückliste lesen/ändern | `IBomTableAnnotation.GetComponents2` (2011 SP03); `ITableAnnotation.InsertColumn2` (4, 2010); `GetColumnType3` | `IView.GetBomTable` nur für Excel-Stücklisten | B | frei |
| Positionsnummern | `IDrawingDoc.AutoBalloon5(Options)` (1, 2012) mit `CreateAutoBalloonOptions` (Layout, IgnoreMultiple …); einzeln `InsertBOMBalloon2`; gestapelt `InsertStackedBalloon2` (2012) | Ansichten/Blatt vorher auswählen; Nummern an Stückliste gekoppelt; lesen `INote.IsBomBalloon`, `GetBomBalloonText` | B | Auswahl |
| Explosionsansicht | `IView.ShowExploded(ShowIt)` | Explosionszustand der Konfiguration der Ansicht | B | frei |
| Normteile nicht schneiden | `swCreateSectionView_ExcludeFasteners=64`; `IDrSection.ExcludeFasteners`, `SetExcludedComponents` (2005) | was als „Fastener“ gilt (nur Toolbox?), unbelegt → sicherer: ausdrückliche Liste aus der Spec | B | frei |
| Schraffur | `IView.GetFaceHatches()` → `IFaceHatch.Pattern`, `Angle`, `Scale2` (2003) | – | B | frei |

### Export

| Aufgabe | Methode (n, seit) | Bedingung / Fallstrick | Beleg | Art |
|---|---|---|---|---|
| Speichern/Export | `IModelDocExtension.SaveAs3` (7, **2020 SP02**); Optionen Silent=1, UpdateInactiveViews=16 | – | B | frei |
| PDF | `ISldWorks.GetExportFileData(swExportPdfData=1)` → `IExportPdfData.SetSheets(AllSheets=1, …)` → `SaveAs3` | `swPDFViewOnSave` (617) abschalten, sonst öffnet sich der Viewer | B | frei |
| DXF/DWG | über Dateiendung; `swDXFDontShowMap=true` (sonst Mapping-Dialog); `swDxfMultiSheetOption` (253) bzw. Blatt für Blatt | Hilfe-Beispiel nutzt noch das überholte `SaveAs4` | A ([Beispiel Save Drawing Sheets as DXF](https://help.solidworks.com/2025/english/api/sldworksapi/Save_Drawing_Sheets_as_DXF_Example_VB.htm)) | frei |

### Grenzen und Fallstricke

| Thema | Befund | Beleg |
|---|---|---|
| Auswahlgetrieben | Ansicht aktivieren → Auswahl leeren → nach Lage auswählen (Blattkoordinaten aus `ModelToViewTransform`) → Aufruf → Rückgabe prüfen → `EditRebuild3` | B (Remarks; Ablauf ist Folgerung) |
| Sichtbarkeit | manche Funktionen setzen ein sichtbares SolidWorks voraus (Ansichten aktualisieren sich sonst nicht) | B ([Programmierleitfaden](https://help.solidworks.com/2025/english/api/sldworksapiprogguide/Overview/API_Functionality_Dependent_on_SolidWorks_Being_Visible.htm)) |
| Neuaufbau | `EditRebuild3` nur im aktiven Dokument; `ForceRebuild3(TopOnly)`; nach `ScaleRatio`, `Position` u. a. Pflicht | B |
| Lightweight | `ResolveOutOfDateLightWeightComponents` braucht Auswahl; Lightweight meldet `IsHidden`/`IsSuppressed` = true | B |
| Namen | `ActivateView` false bei Blatt; `GetName2` bei Schnittansichten nicht eindeutig → `GetUniqueName`; `ReferencedDocument` bei Schnitt leer → `GetBaseView` | B |
| Service Pack | `InsertBomTable6`, `ImportAnnotations`: 2025 FCS; `GetFirstDisplayDimension6`, `GetFirstNote2`, `GetFirstTableAnnotation2`: **2025 SP01**; `GetAnnotationsByType`: **2025 SP02**; `EditSheet2`: 2024 SP02; ISO-21920-Symbol: 2025 SP1 (C) | B ([Release Notes](https://help.solidworks.com/2025/english/api/sldworksapi/ReleaseNotes-sldworksapi.html)) |
| SP auf Rechner A | unbekannt; `swki api pruefe-code` prüft vermutlich nur das Jahr (`seit`), nicht das SP; Abfrage über `ISldWorks.RevisionNumber` nicht nachgeschlagen | C |
| überholte Methoden | funktionieren erfahrungsgemäß weiter (`GetFirstDisplayDimension5`, `SetupSheet5`) | C |
| nicht im Index | `IView.SetSectionedBodies`, `IView.FlatPatternView`, `IModelDocExtension.InsertGtol`, `IModelDoc2.InsertSurfaceFinishSymbol3`, `ITitleBlock.GetEditableNotes`, `IModelDocExtension.GetExportPdfData`, `IDrawingDoc.AutoInsertCenterMarks2`, Mittellinien-Automatik, gesamte `swdimxpert`-Bibliothek | B |
| Speicher/Laufzeit | nicht untersucht | – |

**Zusammenfassung Machbarkeit:**
- **Ohne Auswahl machbar:** Zeichnung, Blatt, Norm, Maßstab, Standard- und Modellansichten, Bruch, Abwicklung, Darstellung, Toleranz- und Passungswerte an vorhandenen Maßen, Notizen, Eigenschaften, Stückliste, Export, Rücklesen (Ansichten, Maße, Annotationen, Anker).
- **Auswahlgetrieben:** Schnitt- und Detailansichten (Skizze vorher anlegen), manuelle und Koordinatenmaße, AutoDimension, Modellmaßübernahme je Ansicht, GTol, Bezüge, Positionsnummern, Bohrungstabelle, Mittellinien.
- **Mit Dialog:** `AddHoleCallout2`.
- **Nicht verfügbar bzw. unbelegt:** ISO-13715-Kantensymbol, automatische Ansichtsanordnung, Hüllquader von Annotationen, dokumentweites Dezimalkomma, DimXpert-API im Index.
- **Für swki naheliegend** (Folgerung Notiz 06): Maße als „für Zeichnung markiert“ im Modell anlegen und mit `DimensionsMarkedForDrawing` + `TolerancedDims` + `holeCallout` übernehmen. Der `bezug` der Spec bestimmt dann die Zeichnungsbemaßung. AutoDimension und manuelle Maße dienen nur als Ergänzung, jeweils gegen die Spec geprüft. Ob swki heute Maße als „für Zeichnung markiert“ anlegt, ist nicht recherchiert.

## Offene Fragen für das Brainstorming der Spec

Hinter jeder Frage steht in Klammern der Befund, der sie auslöst.

**Blatt und Schriftfeld**
1. Gibt es eine Firmenvorlage (Blattformat .slddrt, Zeichnungsvorlage .drwdot, Normdatei .sldstd), oder baut swki eine eigene nach ISO 5457/7200? (Kap. 10: Vorlage ist der robusteste Weg. Norm, Linienstärken, Schrift und Dezimalkomma sind per API nur teilweise bzw. nicht dokumentweit setzbar.)
2. Welche Schriftfeldfelder sind Pflicht, und wie heißen die Eigenschaften? Zur Wahl stehen die acht ISO-7200-Pflichtfelder plus Revisionsindex, Werkstoff, Halbzeug, Masse, Maßstab und Blattanzahl. Was kommt aus dem Teil (Spec `eigenschaften`), was aus der Zeichnung? (Kap. 2: acht Pflichtfelder A; `eigenschaften` ist heute eine freie Map ohne Pflichtschlüssel.)
3. Welches Schema haben Zeichnungs- und Sachnummer, und ist die Zeichnungsnummer gleich der Teilnummer? (Kap. 2 Pflichtfeld Sachnummer; Kap. 9: Stückliste verweist auf die Einzelteilzeichnung.)
4. Revisionsschema (A–Z, dann AA …; I und O meiden?) und Änderungstabelle ja/nein? (Kap. 2 und 9: Revisionsindex optional, Tabelle ohne Quelle.)
5. Stehen Maßstab und Projektionssymbol im oder neben dem Schriftfeld? (Kap. 2: Widerspruch der Quellen.)
6. Wie wird das Format gewählt: automatisch das kleinste passende, A4 hoch oder quer? Liniengruppe 0,5 bis A2 und 0,7 ab A1 übernehmen? (Kap. 2/3.)

**Toleranzen und Oberflächen**
7. Welcher Allgemeintoleranz-Weg: (a) ISO 2768-1 datiert, Klasse m, ohne K; (b) ISO 22081 + DIN 2769 mit Flächenprofil auf A, B, C; (c) Übergang? Und welche Klasse (m oder f)? (Kap. 7: ISO 2768-2 zurückgezogen, undatiertes „mK“ mehrdeutig, neue ISO 2768 ohne Fasen/Radien.)
8. Welcher Tolerierungsgrundsatz: ISO 8015 mit Ⓔ gezielt an Passmaßen, oder pauschale Hülle („Size ISO 14405 Ⓔ“)? Klarstellungsvermerk „Tolerierung ISO 8015“ ins Schriftfeld? (Kap. 7: DIN 7167 zurückgezogen, ohne Angabe gilt Unabhängigkeit.)
9. Oberflächen nach ISO 21920 (setzt laut UI-Hilfe SW 2025 SP1 voraus, C) oder vorerst ISO 1302? Welches Standard-Ra für die Sammelangabe, und welche Funktionswerte (Lagersitz, Passbohrung, RWDR-Fläche)? (Kap. 6, Kap. 10.)
10. Welcher Wert für die Kanten-Sammelangabe nach ISO 13715 (z. B. „entgratet −0,1 … −0,3“, C), und in welcher Form (Notiz oder Block, da keine API gefunden)? (Kap. 5: Außenkanten bleiben im Hausstil ohne Fase; neue ISO 2768 streicht Kantentoleranzen.)
11. Woher kommen Maßtoleranzen, Passungen, Rauheiten und Form-/Lagetoleranzen? Neue Spec-Felder am Feature (z. B. Passung an `bohrung`, H7 als Vorgabe für `normbohrung art: stift`), eigene Zeichnungs-Spec oder Regeln? Gehören sie in die Freigabe-Prüfsumme? (Kap. 7: Spec hat dafür heute keine Felder.)
12. Wer legt Bezüge (A, B, C) und Funktionsflächen fest: Spec-Feld am Teil, Ableitung aus `deckungsgleich`-Verknüpfungen der Baugruppe oder Rückfrage? (Kap. 7/8: Bezug = Passfläche, B; ISO 22081 braucht ein vollständiges Bezugssystem.)
13. Bohrbilder als Positionstoleranz mit theoretisch genauen Maßen (und Ⓜ) oder mit ±-Koordinaten? Ab wie vielen Bohrungen eine Koordinaten- bzw. Bohrungstabelle? (Kap. 4/7: Position funktionsgerechter, B; Tabellenschwelle C.)

**Bemaßungsstil (Hausregeln, wo die Norm schweigt oder Quellen widersprechen)**
14. Welcher Abstand für Maßlinien: erste 10 mm, weitere 7 oder 5 mm? (Kap. 4: Widerspruch, keine Norm.)
15. Bohrungsangabe mit Symbolen ⌴/⌵/↧ oder in Textform (Ø × Tiefe)? Anzahl als „6 × Ø8“ oder „6X Ø8“? (Kap. 4: ISO-Status der Symbole unbelegt.)
16. Fasen als „0,5 × 45°“ (Vorschlag Notiz 02) oder „C0,5“? Bohrungsfase in der Bohrungsangabe? (Kap. 4/8.)
17. Positionsnummern: Kreis ja/nein, Schrifthöhe (größer als Maßzahl? Faktor), Reihenfolge, Winkel der Hinweislinie? (Kap. 9: POS-06/-08/-13/-14 B/C.)
18. Werden Hilfsmaße (Klammer) und Prüfmaße (Rahmen) genutzt, und wann? (Kap. 4: Schreibweise B, Pflicht in ISO 129-1:2018 offen.)
19. Woher kommt die Bemaßung: (a) Modellmaße aus dem Bau mit `bezug` übernehmen („für Zeichnung markiert“); (b) in der Zeichnung neu setzen aus Spec und Funktionsflächen; (c) Mischung? (Kap. 8: Skizzenmaße 1:1 sind ein typischer Fehler. `massplan` bemaßt je Skizze, nicht featureübergreifend. Kap. 10: Weg (a) ist der deterministischste.)
20. Dezimalkomma und Schrifthöhe der Maßzahl (3,5 mm?) fest in der Vorlage? (Kap. 2/10: Komma per API nur Systemoption.)

**Umfang und Ablauf**
21. Was umfasst Etappe 1: nur Einzelteile (prismatische Frästeile), auch Drehteile (Freistich, Zentrierbohrung fehlen als Feature), Blech (swki hat keine Blech-Features), Bestandsdateien? (Kap. 8.)
22. Welche Ausgabeformate: SLDDRW, PDF, DXF, DWG? STEP des Modells beilegen? (Kap. 8: Fictiv und DE-Praxis nennen beide das 3D-Modell; Kap. 10: Export ohne Dialog möglich.)
23. Wie wird geprüft: maschinelle Regeln über API-Rücklesen (welche hart, welche Hinweis), Prüfer-Agent mit Bild bzw. PDF der Zeichnung, Abgleich jedes Pflichtmaßes gegen Spec bzw. Modell (`FullName` + Wert)? (Kap. 2–9 Spalte „prüfbar“; Kap. 10 Rücklesen.)
24. Wie läuft die Freigabe der Zeichnung: Teil der Spec-Freigabe oder eigene Freigabe? Wie wird eine von Hand geänderte Zeichnung erkannt (analog `MANUELL_GEAENDERT`)? (CLAUDE.md-Ablauf; Kap. 10 Rücklesen.)
25. Welches Service Pack haben Rechner A und der Firmenrechner (SW 2026)? Fallbacks nur bis 2025 FCS oder SP-Abfrage beim Start? (Kap. 10: SP01/SP02-Methoden, `pruefe-code` prüft nur das Jahr.)
26. Dürfen die PDFs und Normvorschauen der nächsten Liste geholt werden (je Datei mit OK), und darf die ISO-OBP-Nutzungsbedingung akzeptiert werden? (Belegskala: kein Normtext gelesen.)

**Baugruppe**
27. Welche Stücklistenspalten (Pos., Menge, Einheit, Benennung, Sach-/Zeichnungsnr., Werkstoff/Halbzeug, Norm, Hersteller und Bestellnummer für Kaufteile, Bemerkung)? Normteilbezeichnung im Format „ISO 4762 – M8 × 25 – 8.8“? (Kap. 9: ISO 7573 schreibt nichts vor, DIN 6771-2 zurückgezogen.)
28. Liegt die Stückliste auf der Zeichnung (von unten nach oben, Kopf am Schriftfeld) oder ist sie ein eigenes Dokument? Als Baukasten- oder Strukturstückliste? (Kap. 9: STL-08/-10, SATZ-02.)
29. Welche Komponenten werden im Schnitt nicht geschnitten? Normteile automatisch; Wellen und Achsen bräuchten ein Spec-Kennzeichen. Werden Endlagen aus `bewegungen` als Strich-Zweipunktlinie gezeigt? (Kap. 9: BG-03, BG-05.)
30. Explosionsansicht ja/nein? Welche Maße auf der Baugruppenzeichnung (Anschluss-, Hub-, Gesamtmaße)? Hinweise wie Anzugsmomente? (Kap. 9: BG-06 C, keine Quelle.)

## Quellen, die die Belegstärke heben würden (brauchen OK des Nutzers)

Alle sind öffentliche Leseproben, Inhaltsverzeichnisse oder Hochschul- und Herstellerskripte. Größen sind unbekannt, sofern nicht angegeben. Nichts davon wurde abgerufen.

**Priorität 1 – Normvorschauen (klären Kernfragen der Spec)**

| Datei / Seite | URL | klärt |
|---|---|---|
| ANSI-Vorschau ISO 129-1:2018 | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+129-1-2018.pdf | Symboltabelle ⌴/⌵/↧/C/t=, Maßelemente |
| BSI-Vorschau (vermutlich BS EN ISO 129-1) | https://webstore.ansi.org/preview-pages/BSI/preview_30321494.pdf | wie oben |
| DIN-Inhaltsverzeichnis DIN EN ISO 129-1:2022-02 | https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:333197796/toc-3331584/download | Gliederung, Hilfs-/Prüfmaß |
| iTeh-Vorschau ISO 6433:2012; SIS-Vorschau; alte Ausgabe 1981 | https://cdn.standards.iteh.ai/samples/51527/d4eaa720fb0448bea2952817ce24d508/ISO-6433-2012.pdf ; https://www.sis.se/api/document/preview/914706/ ; https://cdn.standards.iteh.ai/samples/12788/90f43a68f2e84c65b774dd04be8bc4d0/ISO-6433-1981.pdf | Schrifthöhe, Kreis, Methoden b)/c), Anm. 4.1 |
| DIN-Inhaltsverzeichnis DIN EN ISO 6433 | https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:149924295/toc-1872449/download | – |
| iTeh-Vorschau ISO 7573:2008; SIS-Vorschau; Ausgabe 1983 | https://cdn.standards.iteh.ai/samples/43883/2e81effe1cb7450b9cb2b31710cc6107/ISO-7573-2008.pdf ; https://www.sis.se/api/document/preview/910444/ ; https://cdn.standards.iteh.ai/samples/14356/dc95eddbdb164c2f9b528dd9183f3cbd/ISO-7573-1983.pdf | Datenfelder 5.2, Leserichtung |
| iTeh-Vorschau ISO 5457:1999; DIN-TOC DIN EN ISO 5457:2017 | https://cdn.standards.iteh.ai/samples/29017/e46c0ec5d98f470aab82dae76889f229/ISO-5457-1999.pdf ; https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:278410251/toc-2743716/download | Ränder, Zentriermarken, Felder |
| ANSI-Vorschauen ISO 128-2:2020 und 128-2:2022; DIN-TOC DIN EN ISO 128-2:2023 | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+128-2-2020.pdf ; https://webstore.ansi.org/preview-pages/ISO/preview_ISO+128-2-2022.pdf ; https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:361281642/toc-3397887/download | Liniengruppen im Maschinenbau-Anhang |
| ANSI-Vorschauen ISO 128-3:2022 und 128-3:2020 | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+128-3-2022.pdf ; https://webstore.ansi.org/preview-pages/ISO/preview_ISO+128-3-2020.pdf | Ansichten, Schnitte, Einzelheit |
| iTeh-Vorschau ISO 128-22:1999 | https://cdn.standards.iteh.ai/samples/29094/8ae3632c00ce42db8913a415df21f24b/ISO-128-22-1999.pdf | Hinweislinienenden |
| iTeh-Vorschau ISO 5456-2:1996 | https://cdn.standards.iteh.ai/samples/11502/cef8abb25a204691907a077adf420d24/ISO-5456-2-1996.pdf | Projektionssymbol |
| DIN-TOC DIN EN ISO 7200:2004; IS 11665:2010 (identisch ISO 7200, law.resource.org); SP 46 (2003) | https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:69093619/toc-9536385/download ; https://law.resource.org/pub/in/bis/S01/is.11665.2010.pdf ; https://law.resource.org/pub/in/bis/S01/is.sp.46.2003.pdf | Feldlängen, Revisionsindex |
| ANSI-Vorschau ISO 6410-1:1993; iTeh-Vorschau; DIN-TOC DIN EN ISO 6410-3:2021 | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+6410-1-1993.pdf ; https://cdn.standards.iteh.ai/samples/12750/5333999a874f43a4b62d1b73da8f8b2c/ISO-6410-1-1993.pdf ; https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:339761477/toc-3262800/download | Gewindelinien |
| iTeh-Vorschau ISO 13715:1994 (alt, Symbolgrundlagen) | https://cdn.standards.iteh.ai/samples/18124/7cd81dc1f51340b0bf787f532ba240e2/ISO-13715-1994.pdf | Kantensymbol |
| ANSI-Vorschau ISO 2692:2021 | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+2692-2021.pdf | Ⓜ/Ⓛ |
| din.de-Leseproben DIN EN ISO 22081, DIN 2769, DIN EN ISO 21920-1 | https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:356826589/toc-3371761/download ; https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:364625893/toc-3416574/download ; https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:344762052/toc-3294016/download | Schriftfeldnotation 22081, Klassen, Symbol 21920 |
| ISO-OBP-Vorschau (iso.org/obp) | – | verlangt Zustimmung zu Nutzungsbedingungen („I have read and agree to the Terms of Use“); nur mit OK |

**Priorität 2 – Lehr- und Praxisunterlagen**
- RUB „Beschreibung fertigungsgerechte Bemaßung“ (OER; wichtigste Quelle für Frästeil-Bezugskanten, Bohr- vs. Fräsmaschine, Wellen): https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598368/mod_resource/content/9/Beschreibung%20fertigungsgerechte%20Bema%C3%9Fung_meta_lizenz.pdf. Dazu Aufgaben „Mittel Lösungen“ und „Schwer“: https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598372/mod_resource/content/9/Aufgaben%20zum%20Bema%C3%9Fen%20Mittel%20L%C3%B6sungen_meta_lizenz.pdf ; https://moodle.ruhr-uni-bochum.de/pluginfile.php/5598373/mod_resource/content/9/Aufgaben%20zum%20Bema%C3%9Fen%20Schwer_meta_lizenz.pdf
- TUM „Zeichnungserstellung.pdf“ (in vier Notizen genannt: Linien, Schnitte, Pfeil, Überstand, Schrift, nicht geschnittene Teile, Überbemaßung): https://www.epe.ed.tum.de/fileadmin/w00bzo/ewt/Werkstatt/Zeichnungserstellung.pdf. Dazu TUM „Allgemeintoleranzen_nach_DIN_ISO_2768.pdf“: https://www.epe.ed.tum.de/fileadmin/w00bzo/ewt/Werkstatt/Allgemeintoleranzen_nach_DIN_ISO_2768.pdf
- Allgemeintoleranzen ISO 22081:
  - IHK „gps-allgemeine-toleranzen-data.pdf“: https://www.ihk.de/blueprint/servlet/resource/blob/5831308/d01f30113d287172380e5da5f9cefce1/gps-allgemeine-toleranzen-data.pdf
  - Hexagon „049-FMT“: https://bynder.hexagon.com/m/6acb6f81db21e367/original/049-FMT_Allgemeintoleranzen-nach-ISO-22081.pdf
  - QZ 10/2021 „Korrekte Toleranzen für Form und Lage“: https://res.cloudinary.com/sternwald-systems/raw/upload/v1/hugoprd/ARTIKEL_ATTACH/002D64BC_30E7B0F87C2C/aec4c0462e3e110e3c47d7919445d135eeaab3f0/Korrekte%20Toleranzen%20%20f_r%20Form%20und%20Lage%20-%20QZ%2010%202021.pdf
- Tolerierung und Prüfung:
  - Zeiss-Leseprobe „prüfgerechte Tolerierung“ (in zwei Notizen genannt): https://www.zeiss.at/content/dam/metrology/services/training/training-packages/pruefgerechte-tolerierung-mass-form-lage-leseprobe.pdf
  - Zeiss-Forum-PDFs: https://qualityforum.zeiss.com/migration/images/3487_c36864f7450b7ff000f8142e1a4091a9.pdf ; https://qualityforum.zeiss.com/migration/images/241_ddddae37f957c16edfa7d5f1a2f8b076.pdf
  - Werth „Funktionsgerechte Prüfung mit virtueller Lehre“: https://www.Werth.de/fileadmin/import/data/Bilder/ueberwerth/Veroeffentlichungen/Praxistipps/Veroeffentlichungen_Praxistipps_Funktionsgerechte-Pruefung-mit-virtueller-Lehre.pdf
  - cad.de „Tolerierungsgrundsaetze.pdf“: https://ww3.cad.de/foren/ubb/uploads/Dieter+Fischer/Tolerierungsgrundsaetze.pdf
- Oberflächen:
  - Polytec ISO 21920: https://www.polytec.com/_Resources/Persistent/d/0/9/0/d0904958bae5a1ddfbc1566c6804508e7e813280/OM_GL_TOP_Rauheitsmessung-ISO-21920_D_52164.pdf
  - HAW Hamburg Rauheitsposter: https://www.haw-hamburg.de/fileadmin/TI-MP/PDF/IWS/Vorlesungen_Labore/Oberfl%C3%A4chentechnik_OFT/Rauheitsposter/Rauheitsposter.pdf
  - Uni Stuttgart IMA 104170 (RWDR): https://www.ima.uni-stuttgart.de/dokumente/forschung/dichtungstechnik/dienstleistungen/104170.pdf
- Lagersitze: SKF https://cdn.skfmediahub.skf.com/api/public/0901d1968037e71a/pdf_preview_medium/0901d1968037e71a_pdf_preview_medium.pdf ; GMN https://www.gmn.de/wp-content/uploads/GMN_Infoblatt_Precision-of-associated-components_en.pdf
- Darstellung und Schrift:
  - Uni Wuppertal CAD-m1: https://www.gds.uni-wuppertal.de/fileadmin/_migrated/content_uploads/CAD-m1.pdf
  - HS Schmalkalden Schnitte: https://npr.hs-schmalkalden.de/files/WIWKonstruktion1Tutorien/Dokument3Schnitte.pdf
  - GWS Lörrach: https://gws-loerrach.de/wp-content/uploads/2025/11/technisches-zeichnen-techniker-meister.pdf
  - schule-bw „Regeln zum technischen Zeichnen“: https://www.schule-bw.de/faecher-und-schularten/praktische-faecher/technik/unterrichtsmaterialien/tz/REGELN%20ZUM%20TECHNISCHEN%20ZEICHNEN-lang.pdf/@@download/file/REGELN%20ZUM%20TECHNISCHEN%20ZEICHNEN-lang.pdf
  - Vieweg-Leseprobe Schrift: https://beckassets.blob.core.windows.net/product/readingsample/11027421/9783528039684_firstchapter_009.pdf
  - Europa-Lehrmittel Bautechnik: https://www.bauberufe.eu/images/doks/zeichnen_414156.pdf
- Leseproben Europa-Lehrmittel, Hanser und Christiani:
  - Europa-Lehrmittel 14340, 12814, 13519: https://www.europa-lehrmittel.de/leseprobe/14340-1.pdf ; https://www.europa-lehrmittel.de/leseprobe/12814-11.pdf ; https://www.europa-lehrmittel.de/leseprobe/13519-12.pdf
  - Hanser Grollius: https://files.hanser.de/Files/Article/ARTK_LPR_9783446477056_0001.pdf ; https://files.hanser.de/Files/Article/ARTK_LPR_9783446478909_0001.pdf
  - Christiani Gewinde: https://www.christiani.de/out/media/pdf/80521-leseprobe.pdf
- Fertigung:
  - TU Chemnitz Abtriebswelle: https://tu-chemnitz.de/mb/mp/lehre/cae/creo/tutorials/data/CAD_AK/03_Abtriebswelle_Creo3_einteilig.pdf
  - TU Chemnitz Baugruppenzeichnung/Stückliste: https://tu-chemnitz.de/mb/mp/lehre/cae/creo/tutorials/data/CAD_AK/09_Baugruppenzeichnung_Stückliste_Creo4_einteilig.pdf
  - handwerk-technik Blech: https://www.handwerk-technik.de/_files_media/probeseiten/3208_02.pdf
  - Protolabs Blech-Toleranzen: https://protolabs.com/media/roognect/sheet-metal-tolerances-one-pager-2.pdf

**Priorität 3 – SolidWorks**
- „What's New 2026“: https://files.solidworks.com/Supportfiles/Whats_new/2026/english/whatsnew.pdf
- CADMicro „SOLIDWORKS 2025 Enhancements E-Book“: https://cadmicro.com/wp-content/uploads/Solidworks-2025-Enhancements-E-Book.pdf
- GoEngineer „MBD Data Sheet“: https://cdn.goengineer.com/solidworks_mbd_data_sheet.pdf

**Nicht verwenden** (vermutlich unrechtmäßige Volltexte): model-r.ru `din_iso_13715_2000.pdf`, Scribd-Kopien von Normen (ISO 13715, IS 15726 u. a.), idoc.pub-Scan „Hoischen – Technisches Zeichnen“, Studocu, pdfcoffee, kupdf.

**Vorfall:** Die URL https://tu-dresden.de/ing/maschinenwesen/imm/vpe/ressourcen/dateien/dateien_forschung/informationen-profiltoleranz (ohne .pdf-Endung) lieferte unerwartet ein PDF (455,7 KB). Das Abrufwerkzeug hat es automatisch im Sitzungsordner `tool-results` abgelegt. Die Datei wurde **nicht geöffnet und nicht verwendet**. Sie hat nichts zu tun mit der gelesenen HTML-Seite der TU Dresden „Hinweise für Biegeteile“ (Kap. 8).

## Quellenverzeichnis

**Normstatus (Kap. 1):**
- DIN Media / din.de:
  - [5457](https://www.dinmedia.de/de/norm/din-en-iso-5457/278410251)
  - [7200](https://www.din.de/en/wdc-beuth:din21:69093619)
  - [5455](https://www.dinmedia.de/en/standard/din-iso-5455/790721)
  - [3098-1](https://www.dinmedia.de/en/standard/din-en-iso-3098-1/232192579)
  - [128-2](https://www.dinmedia.de/de/norm/din-en-iso-128-2/361281642)
  - [128-24](https://www.dinmedia.de/de/norm/din-iso-128-24/23592503)
  - [128-3](https://www.dinmedia.de/en/standard/din-en-iso-128-3/359489181)
  - [128-50](https://www.dinmedia.de/en/standard/din-iso-128-50/46948186)
  - [129-1:2022](https://www.dinmedia.de/de/norm/din-en-iso-129-1/333197796)
  - [129-1:2020](https://www.dinmedia.de/de/norm/din-en-iso-129-1/314070706)
  - [EN ISO 129-1](https://www.dinmedia.de/en/standard/en-iso-129-1/314939822)
  - [406-10](https://6sku3uaup9f9.din.de/en/standard/din-406-10/1990706)
  - [406-11](https://dinmedia.de/en/standard/din-406-11/1991065)
  - [406-11 Bbl. 1](https://www.dinmedia.de/de/technische-regel/din-406-11-beiblatt-1/36566358)
  - [406-2](https://www.dinmedia.de/en/standard/din-406-2/2202245)
  - [406-5](https://www.dinmedia.de/en/standard/din-406-5/103718943)
  - [15786](https://www.din.de/en/wdc-beuth:din21:223068266)
  - [13715](https://www.dinmedia.de/de/norm/din-en-iso-13715/314070606)
  - [6410](https://www.dinmedia.de/en/standard/din-iso-6410/2584244)
  - [6410-3](https://din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:338987523)
  - [2768-1](https://www.din.de/de/wdc-beuth:din21:1718351)
  - [2768-2](https://dinmedia.de/en/standard/din-iso-2768-2/1677248)
  - [22081](https://www.din.de/en/wdc-beuth:din21:356826589)
  - [2769](https://www.dinmedia.de/de/norm/din-2769/364625893)
  - [E 2769](https://www.dinmedia.de/de/norm-entwurf/din-2769/404718083)
  - [E 2768](https://www.dinmedia.de/de/norm-entwurf/din-en-iso-2768/394170392)
  - [7167](https://www.dinmedia.de/de/norm/din-7167/1333468)
  - [14405-1](https://www.dinmedia.de/en/standard/din-en-iso-14405-1/132686225)
  - [5459:2025](https://www.dinmedia.de/de/norm/din-en-iso-5459/385519058)
  - [5459 Entwurf](https://www.dinmedia.de/en/draft-standard/din-en-iso-5459/380412147)
  - [21920-1](https://www.dinmedia.de/de/norm/din-en-iso-21920-1/344762052)
  - [6433](https://www.dinmedia.de/de/norm/din-en-iso-6433/149924295)
  - [199-1](https://www.dinmedia.de/en/standard/din-199-1/46493205)
  - [509](https://www.dinmedia.de/de/norm/din-509/359215693)
  - [6411](https://6sku3uaup9f9.din.de/en/standard/din-iso-6411/3044538)
  - [36-2](https://www.dinmedia.de/en/draft-standard/din-36-2/250206899)
  - [6771-2](https://www.din.de/en/getting-involved/standards-committees/natg/publications/wdc-beuth:din21:1433478)
- ISO und Normenhandel:
  - ISO: [64007](https://www.iso.org/standard/64007.html), [42099](https://www.iso.org/standard/42099.html), [12750](https://committee.iso.org/standard/12750.html)
  - SIS: [129-1 A1](https://www.sis.se/produkter/terminologi-och-dokumentation/dokumentation-av-tekniska-produkter/ss-en-iso-129-12019a12021/), [128-2](https://www.sis.se/en/produkter/standardization/technical-drawings/general/iso-128-22020/), [128-3](https://www.sis.se/en/produkter/standardization/technical-drawings/general/iso-128-32020/)
  - [BSI 13715](https://knowledge.bsigroup.com/products/technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning)
  - EVS: [13715](https://www.evs.ee/en/evs-en-iso-13715-2019), [2692](https://www.evs.ee/en/evs-en-iso-2692-2021)
  - [genorma 2768-2](https://genorma.com/en/standards/iso-2768-2-1989), [genorma 7573](https://genorma.com/en/standards/iso-7573-2008)
  - [Austrian Standards](https://austrian-standards.at/de/shop/iso-2768-2-1989-1989-11-02~p1222103)
  - [SNV 1101](https://insights.snv.ch/en/page/how-to-comply-with-iso-11012017-a-comprehensive-gu-en)
  - standards.ie: [1101](https://shop.standards.ie/en-ie/standards/din-en-iso-1101-2017-09-409769_saig_din_din_925799), [6433](https://shop.standards.ie/en-ie/standards/iso-6433-2012-581291_saig_iso_iso_1330605)
  - SAI Global: [6410-1](https://infostore.saiglobal.com/en-us/standards/iso-6410-1-1993-591686_saig_iso_iso_1355305/), [7573](https://infostore.saiglobal.com/en-us/standards/iso-7573-2008-584540_saig_iso_iso_1338544/)
  - [Wikipedia EN ISO 128](https://en.wikipedia.org/wiki/ISO_128)

**Blatt, Linien, Darstellung (Kap. 2–3):**
- [checkedcalc](https://checkedcalc.com/learn/technical-drawings/anatomy-of-an-engineering-drawing/)
- Wikipedia DE: [Schriftfeld](https://de.wikipedia.org/wiki/Schriftfeld), [Technisches Zeichnen](https://de.wikipedia.org/wiki/Technisches_Zeichnen)
- [Wikipedia EN ISO 7200](https://en.wikipedia.org/wiki/ISO_7200)
- ingenieurkurse: [Maßstäbe](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/massstaebe-nach-din-iso-5455.html), [Linien](https://www.ingenieurkurse.de/grundlagen-der-technischen-kommunikation/allgemeine-hinweise-zur-gestaltung-von-technischen-zeichnungen/linien-linienarten-und-deren-anwendung.html)
- [Wikibooks Linien](https://de.wikibooks.org/wiki/Technisches_Zeichnen/_Linien_und_Beschriftung)
- [wiechmann-at.de](http://www.wiechmann-at.de/MBStudium/TechnischesZeichnen/TZSchriften.html)
- [lehrerfreund](https://www.lehrerfreund.de/technik/1s/technisches-zeichnen-stricharten-strichstaerken/4482)
- [mechatronik-automatisierung.com](https://mechatronik-automatisierung.com/technische-doku/zeichnung-lesen/schnitte/)
- [Onshape Bruchansicht](https://cad.onshape.com/help/de_DE/Content/Drawing/break_view.htm)
- [draftsperson.net](https://blog.draftsperson.net/drawing-sheet-layout-metric/)

**Bemaßung, Gewinde, Kanten (Kap. 4–5):**
- [Wikipedia DE Bemaßung](https://de.wikipedia.org/wiki/Bema%C3%9Fung)
- [Wikibooks Maßeintragung](https://de.wikibooks.org/wiki/Technisches_Zeichnen/_Ma%C3%9Feintragung)
- schule-bw: [1](https://schule-bw.de/resolveuid/55248110505c4e37b9ea1eec8c92beac), [2](https://schule-bw.de/resolveuid/6051e1eb3c8f4608a14afb7cafe79872)
- [item24](https://glossar.item24.com/en/glossary-index/article/item//dimensioning.html)
- werk24: [ISO vs ASME](https://werk24.io/blog/iso-vs-asme-technical-drawing-standards-complete-comparison), [Symbols](https://werk24.io/knowledge-base/symbols), [Edges](https://werk24.io/knowledge-base/edges)
- [Wikipedia EN Abbreviations](https://en.wikipedia.org/wiki/Engineering_drawing_abbreviations_and_symbols)
- Eng-Tips: [1](https://www.eng-tips.com/threads/basic-dimensioning-of-holes-cbores-amp-csinks-per-iso-standard.228508), [2](https://www.eng-tips.com/threads/bs-8888-vs-iso-15786-hole-callouts.500689)
- [WTCS](https://wtcs.pressbooks.pub/blueprintreading/?p=345)
- [Frankfurt UAS](https://campuas.frankfurt-university.de/mod/resource/view.php?id=263332)
- [hausjournal.net](https://hausjournal.net/gewinde-bemassen)
- [brainbound](https://www.brainbound.blog/chamfer-notation-guide)
- [Zeiss Forum](https://qualityforum.zeiss.com/topic/5842-radiuses-and-chamfers-with-c-t-symbol/)
- [JSA](https://webdesk.jsa.or.jp/preview/pre_jis_b_00028_000_000_2017_j_ed10_ch.pdf)
- [Christiani](https://www.lehmanns.ch/media/87204491)
- [tutory](https://www.tutory.de/entdecken/dokument/gewindeschneider-1.pdf?t=2128)
- [Onshape Gewinde](https://cad.onshape.com/help/de_DE/Content/PartStudio/external_thread.htm)
- [modulusmetal](https://www.modulusmetal.com/iso-13715-technical-product-documentation-edges-of-undefined-shape-indication-and-dimensioning)
- [Autodesk Fusion](https://help.autodesk.com/cloudhelp/ENU/Fusion-Drawing/files/DWG-REF-EDGE-SYMBOL.htm), [AutoCAD Mechanical](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-Mechanical/files/GUID-9DFD5C29-5666-4AC8-9C94-8BE7BE9E4392.htm)
- [Hanser Grollius](https://files.hanser.de/Files/Article/ARTK_LPR_9783446478909_0001.pdf)

**Oberflächen, Toleranzen (Kap. 6–7):**
- [Wevolver](https://www.wevolver.com/article/iso-2768-general-tolerances-tables-classes-current-status)
- [amesweb](https://amesweb.info/fits-tolerances/iso-2768-linear-dimensions-tolerances.aspx)
- [GPSlife](https://gpslife.de/en/?p=1417)
- [Wikipedia DE Allgemeintoleranz](https://de.wikipedia.org/wiki/Allgemeintoleranz)
- iteh: [22081](https://standards.iteh.ai/catalog/standards/iso/5bb1f91d-50a4-44cf-bdbf-3652b92dd8ee/iso-22081-2021), [FDIS 2768](https://standards.iteh.ai/catalog/standards/iso/0c8e062e-4aa9-48d5-a245-94ade8dfd018/iso-fdis-2768), [1101](https://iteh.es/catalog/standards/iso/8171a5e2-c3f2-4bbe-997a-ad8f3e82969c/iso-1101-2017)
- [dHWN Werknorm](https://www.dietzel-hydraulik.de/fileadmin/user_upload/dokumente/downloads/technische_informationen/WERKNORM-dHWN-IV_20220228.pdf)
- [Hansgrohe](https://assets.hansgrohe.com/celum/web/Anweisung-zur-Ermittlung-von-Messdaten_2020.pdf)
- [TU Darmstadt Passungen](https://www.iim.maschinenbau.tu-darmstadt.de/CAD-Tutorial/CAD-Norminfo/3_important_standards_and_data_sheets/3_tolerances_and_fits/1_selection_and_calculation_of_fits/index.en.html)
- [simplybearings](https://simplybearings.co.uk/shop/Info-Pages-ISO-Limits/c4746_4779/index.html)
- [Hubs](https://www.hubs.com/knowledge-base/understandings-clearance-transition-and-interference-fit/)
- [Wikipedia Engineering fit](https://wikipedia.com/wiki/Slip_fit)
- [JTEKT](https://www.jtekt.co.jp/products/bearing/en/support/bearing-knowledge/14-1000.html)
- [Keyence](https://www.keyence.de/ss/products/measure-sys/gd-and-t/basic/tolerance-entry-frame.jsp)
- [americanbobcat](https://americanbobcat.blog/2021/12/01/mechanical-design-engineering-geometrical-dimensioning-and-tolerancing_what-is-the-position-tolerance)
- [gdandtbasics](https://app.gdandtbasics.com/symbol/true-position)
- [PTC](https://support.ptc.com/help/creo/creo_plus/usascii/model-based_definition/rule_set_2.html)
- [standard.no 2692](https://online.standard.no/en/iso-2692-2021)
- [BSI 21920](https://knowledge.bsigroup.com/products/geometrical-product-specifications-gps-surface-texture-profile-indication-of-surface-texture)
- Digital Surf: [Guide](https://guide.digitalsurf.com/en/guide-iso-21920-parameters.html), [Blog](https://www.digitalsurf.com/blog/how-is-surface-texture-indicated-on-drawings/)
- [Quality Magazine](https://www.qualitymag.com/articles/98952-evolving-roughness-standards-understanding-and-implementing-iso-21920)
- [Wikipedia DE Rauheit](https://de.wikipedia.org/wiki/Rauheit)
- [JLCCNC](https://jlccnc.com/blog/surface-roughness)
- [Dichtomatik](https://www.fst.com/de/-/media/files/dichtomatik/solution-sheets/de/dichtomatik_radial-wellendichtringe.pdf)
- [DGQ Symbole](https://formativ.dgq.de/wp-content/uploads/2023/11/DGQ_ISO-GPS_Symbole-und-Abkuerzungen_2023_11_01.pdf)

**Fertigungsgerecht (Kap. 8):**
- [Cambridge Network](https://www.cambridgenetwork.co.uk/index.php/news/art-dimensioning-cad-drawings-cnc-machining-traditional-fraftsmans-approach)
- [Fictiv](https://www.fictiv.com/articles/9-tips-for-better-engineering-drawings-that-save-time-money)
- [buffl.co](https://buffl.co/community/c/6946dd6ba18ba13579567696)
- [clean-invoice](https://www.clean-invoice.com/feinwerkmechanik/checkliste-feinwerkmechanik)
- [TU Dresden Biegeteile](https://tu-dresden.de/ing/elektrotechnik/die-fakultaet/fakultaetswerkstatt/werkstattteil-praezisionsmechanik/hinweise-fuer-biegeteile)
- [Protolabs](https://protolabs.com/services/sheet-metal-fabrication/design-guidelines)
- [cad.de Blech](https://ww3.cad.de/foren/ubb/uploads/user/Blechkonstruktionen[1].pdf)
- Wikipedia DE: [Freistich](https://de.wikipedia.org/wiki/Freistich), [Passfeder](https://de.wikipedia.org/wiki/Passfeder)
- [HAW Hamburg BA](https://reposit.haw-hamburg.de/bitstream/20.500.12738/18315/1/BA_Finite-Elemente-Analysen%20zum%20nichtlinearen%20Tragverhalten%20von%20Passfederverbindungen_geschw%c3%a4rzt.pdf)
- [gpslife 1036](https://gpslife.de/en/?p=1036)
- [mfgrobots](https://www.mfgrobots.com/Article/mfg/it/54233.html)
- [industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/engineering-drawing-dimensioning-best-practices-guide)
- [rivcut](https://rivcut.pages.dev/blog/drawing-callouts-guide)
- [WTCS Kette](https://wtcs.pressbooks.pub/blueprintreading/?p=154)
- [woodworker.de](https://www.woodworker.de/forum/goto/post?id=621915)

**Baugruppe (Kap. 9):**
- iTeh: [EN ISO 6433](https://standards.iteh.ai/catalog/standards/cen/b35bb0cd-5f83-46b2-9c85-ef0a7848124f/en-iso-6433-2012), [SIST EN ISO 6433](https://standards.iteh.ai/catalog/standards/sist/d1b5a81a-3542-445d-94f7-e25a9ecf7543/sist-en-iso-6433-2012), [SIST ISO 7573](https://standards.iteh.ai/catalog/standards/sist/bbd903b9-abf9-44d0-a828-9dd6e0d56f56/sist-iso-7573-2010), [ISO 7573:1983](https://standards.iteh.ai/catalog/standards/iso/c486fd85-38de-460c-907c-b2acf8a13f15/iso-7573-1983), [ISO 128-22](https://standards.iteh.ai/catalog/standards/iso/225fb29c-8da9-432d-a5b9-9cfc021ac313/iso-128-22-1999), [ISO 7200](https://standards.iteh.ai/catalog/standards/iso/cda0743a-d12c-45c6-87fd-4e96ffda6041/iso-7200-2004)
- [iteh.es ISO 128-3](https://iteh.es/catalog/standards/iso/7a9da10e-d4e1-469f-8837-5df5790a32a0/iso-128-3-2020)
- [BSI 6433](https://knowledge.bsigroup.com/products/technical-product-documentation-part-references-part-references)
- [RoyMech](https://www.roymech.co.uk/Useful_Tables/Drawing/Item_Ref.html)
- TUD: [Explosionszeichnung](https://www.iim.maschinenbau.tu-darmstadt.de/kursunterlagen/plcm_tutorials/CAD/TPD/Explosionszeichnung/), [cad_ss16](https://www.iim.maschinenbau.tu-darmstadt.de/kursunterlagen_archiv/cad_ss16/732_explosionsdarstellung_mit_stckliste_und_positionsnummern_anpassen.html)
- [maschinenbau-wissen.de](https://www.maschinenbau-wissen.de/skript3/konstrkution-entwicklung/technisches-zeichnen/171-positionsnummern)
- [technisches-zeichnen.net](https://www.technisches-zeichnen.net/technisches-zeichnen/grundkurs-02/gruppenzeichnungen-positionsnummern.php)
- [CAD Setter Out](https://cadsetterout.com/drawing-standards/technical-drawing-standards-leader-lines/)
- Wikipedia DE: [Stückliste](https://de.wikipedia.org/wiki/St%C3%BCckliste), [Explosionszeichnung](https://de.wikipedia.org/wiki/Explosionszeichnung)
- [Streit Software](https://www.streit-software.de/vorlagen/stueckliste-vorlage)
- [Böllhoff](https://eshop-pl.boellhoff.com/en/Screws/Screws-with-internal-force-application/Cylinder-screws/Cylinder-screws-/-17.html)
- [Wiley Register](https://application.wiley-vch.de/books/sample/3527709665_bindex.pdf)

**SolidWorks-API (Kap. 10):**
- Offline-Index der API-Hilfe 2025 (Seiten unter https://help.solidworks.com/2025/english/api/, einzeln in Kap. 10 verlinkt)
- [Release Notes](https://help.solidworks.com/2025/english/api/sldworksapi/ReleaseNotes-sldworksapi.html)
- codestack: [Bemaßen](https://www.codestack.net/solidworks-api/document/drawing/view-dimension-model-entities/), [Auswahl](https://www.codestack.net/solidworks-api/document/selection/drawing-view-entities/)
- 3DSwym-Forum: [1](https://3dswym.3dexperience.3ds.com/question/solidworks-user-forum/issues-with-insertmodelannotations3-functionality-in-a-macro_JI9h6O37SnKDHSOfSFpUQQ), [2](https://3dswym.3dexperience.3ds.com/post/solidworks-user-forum/getting-assembly-dimensions-in-a-drawing_bMKA0hDxQ_CkjESvvGDfCw)
- [Hilfe 2020 Auto Dimension Scheme](https://help.solidworks.com/2020/English/SolidWorks/sldworks/HIDD_SWIFT_GTS.htm)
- [centralinnovation](https://centralinnovation.com/resources/auto-dimension-scheme)
- [Hawkridge](https://hawkridgesys.com/blog/mbd-dimxpert-and-mbd-dimensions-whats-the-difference)
- [GoEngineer](https://www.goengineer.com/blog/introduction-dimxpert-solidworks)
- [Javelin 2026](https://www.javelin-tech.com/3d/drawings-whats-new-in-solidworks-2026/)
- [CADimensions](https://knowledge.cadimensions.com/knowledge/what-are-drawing-property-links)
- [forum.solidworks.com](https://forum.solidworks.com/thread/98928)
- SolidWorks-Hilfe Positionsnummern: [2016](https://help.solidworks.com/2016/English/SolidWorks/Sldworks/t_Numbering_Balloons_Sequentially.htm), [2017](https://help.solidworks.com/2017/English/SolidWorks/Sldworks/c_Balloon_Styles_and_Sizes.htm)
