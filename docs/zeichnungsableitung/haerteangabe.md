# Zeichnungsableitung – Nachrecherche Wärmebehandlung, Oberflächenbehandlung, Halbzeug

Datum: 2026-11-17 · Status: Recherche (Plan Z1, Task 2), Grundlage für die Spec-Felder `behandlung` und `halbzeug`
(Design-Spec `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`, Abschnitt 4.1)

## Kurzfassung

- **Norm für Härteangaben:** DIN ISO 15787:2018-08 (= ISO 15787:2016, 40 S.). Sie ersetzt DIN ISO 15787:2010-01. Eine
  „DIN EN ISO 15787“ wurde nicht gefunden. ISO 15787:2016 wurde 2024 bestätigt. Vorgänger in DE war DIN 6773 (zurückgezogen).
- **Schreibweise der Härte hängt von der Ausgabe ab.**
  - „gehärtet und angelassen 58+4 HRC“ (einseitige Plustoleranz ohne Klammern) ist der Stil von DIN 6773 bzw. DIN ISO
    15787:2010. Lehrseiten und Praxis nutzen ihn bis heute.
  - Die Ausgabe 2016/2018 schreibt den Härtewert mit Grenzabmaßen in Klammern, symmetrisch oder einseitig, z. B.
    „(62 ± 2) HRC“ bzw. „(64 0/−4) HRC“. Den Normtext haben wir nicht gesehen.
  - „58+4 HRC“ ist darum **nicht** als aktueller Normwortlaut zu führen. Welcher Stil gilt, ist eine Hausregel-Entscheidung.
- **Härtetiefen:**
  - CHD (früher Eht) mit Grenzhärte 550 HV1 im Regelfall: A.
  - SHD (Randschichthärten) mit Grenzhärte 80 % der Mindest-Oberflächenhärte: B, eine Quelle ordnet die 80 % der CHD zu.
  - NHD (Nitrieren) mit Kernhärte + 50 HV0,5: B.
  - CLT (Verbindungsschicht) in µm: B.
  - Die Bestimmung regelt DIN EN ISO 18203:2026-05. Die neue Ausgabe nimmt CLT dort heraus.
- **Örtliche Behandlung:** breite Strichpunktlinie außerhalb der Kontur, mit Bemaßung: A. Die Linien für „darf behandelt
  werden“ und „darf nicht behandelt werden“ unterscheiden sich zwischen den Ausgaben 2010 und 2018 (Widerspruch, B).
- **Beschichtungen – zwei Bezeichnungssysteme:**
  - Zink nach ISO 2081 mit einfachem Schrägstrich, z. B. „Fe/Zn8/C“. Die Kennbuchstaben sind je Ausgabe verschieden und in
    den Quellen widersprüchlich.
  - Zink und Zinklegierung Cr(VI)-frei nach DIN EN ISO 19598:2017-04 (ersetzt DIN 50979) mit Doppelschrägstrich, z. B.
    „Fe//Zn8//Cn//T0“ (A).
  - Das „Fe//Zn8//C“ aus der Aufgabe vermischt beide Systeme.
- **Eloxal und Brünieren:** Eloxal nach DIN 17611:2022-08 (Kurzzeichen E6/EV1, Schichtdickenklasse in µm) bzw. ISO 7599:2018.
  Brünieren nach DIN 50938:2025-06. Normausgaben B, Zeichnungswortlaut C.
- **Halbzeug – Wechsel bei Blankstahl:**
  - DIN EN 10278:2024-01 gilt nur noch für nichtrostende und besondere Stähle (A).
  - Unlegierter und legierter Blankstahl (C45+C, 11SMnPb30+C …) steht laut Suchauszug in DIN EN ISO 683-7:2025-02, die
    DIN EN 10277:2018-09 ersetzt (B).
  - Bezeichnungsmuster für Flach- und Rundstab nach EN 10058/10060: B (eine Lehrquelle).
- **Rohe Flächen:** Das Symbol „Materialabtrag nicht zulässig“ (Kreis im Wurzelzeichen) ist für ISO 1302 belegt (A). Seine
  Form in ISO 21920-1, die Sammelangabe in Klammern und ein Vermerk „Halbzeugoberfläche“ bleiben C.
- **Feldvorschlag:** Abschnitt 5. Die Härte wird strukturiert geführt (Wert, plus, minus, Verfahren), der Wortlaut entsteht
  über eine Stilwahl (`iso15787_2016` | `din6773`). Einträge bekommen eine optionale `id`, damit zwei Zonen gleicher `art`
  unterscheidbar bleiben.

## Belegskala und Quellenlage

Die Skala ist dieselbe wie in `recherche.md`, Abschnitt „Belegskala und Quellenlage“.

| Grad | Bedeutung |
|---|---|
| **A** | ≥ 2 unabhängige Quellen stimmen überein (mindestens eine davon gelesen) |
| **B** | eine Quelle, oder die Aussage liegt nur als Suchauszug einer nicht geöffneten Seite oder PDF vor (Suchauszug höchstens B) |
| **C** | unbelegt bzw. Hintergrundwissen. In den Tabellen als „C, unbelegt“ markiert, nicht verwenden ohne Gegenprüfung |

**Quellenlage dieser Notiz:**
- **Normvolltexte nicht gelesen.** ISO 15787, ISO 2081, ISO 19598, ISO 7599, DIN 17611, DIN 50938 und EN 10058/10060/10278
  sind kostenpflichtig. Die iTeh-Katalogseite zu ISO 15787:2016 lädt ihren Inhalt per JavaScript und lieferte nur den Kopf.
- **Gelesene HTML-Seiten:**
  - DIN Media zu DIN ISO 15787:2018-08, DIN EN ISO 18203:2026-05, DIN EN 10278:2024-01 und DIN EN ISO 683-7 (nur Titel)
  - genorma ISO 15787:2016
  - Arnold-Horsch-Wiki (Wärmebehandlungsangaben; Fachwiki eines Wärmebehandlungs-Sachverständigen, bezieht sich auf
    DIN ISO 15787:2010-01, Stand 15.11.2026)
  - maschinenbau-wissen.de und technisches-zeichnen.net (Härteangaben)
  - Modulus Metal (ISO-2081-Bezeichnung) und Ramo (Kurzzeichentabelle)
  - Wikipedia DE „Flachstahl“
  - Digital Surf Guide (ISO-1302-Angaben)
- **Alles Weitere ist Suchauszug.** Bei mehreren Zeilen ist der „Auszug“ eine Zusammenfassung des Suchwerkzeugs, kein
  wörtlicher Text. Auch WebFetch-Antworten sind Zusammenfassungen eines Modells. Wörtlich zitiert wird darum nichts, die
  Beispiele sind sinngemäß.
- **Keine PDFs abgerufen.** Keine URL ohne .pdf-Endung lieferte unerwartet ein PDF. Mehrere din.de-Links „…/download“ sind
  vermutlich PDFs (Inhaltsverzeichnisse) und stehen unter „PDF-Kandidaten“.
- **Nicht als Beleg verwendet:** Scribd (Leitfaden Härten, ISO-DIN-Matrix mit „Fe/Zn12/A“), quizlet, Händlerseiten ohne
  Normbezug.
- **Normausgaben gehören als Daten in eine Tabelle**, nicht in den Code (Repo-Regel).

Die Spalte „Hinweis“ nennt Bezug zu swki, Ausgabeabhängigkeit und Vorbehalte.

## 1. Normenstand

| Norm (Thema) | Gültige Ausgabe (DE) | Ersetzt / Status | Quelle (URL) | Beleg | Hinweis |
|---|---|---|---|---|---|
| ISO 15787 (Wärmebehandelte Teile aus Eisenwerkstoffen – Darstellung und Angaben) | **DIN ISO 15787:2018-08** (= ISO 15787:2016), 40 S. | ersetzt DIN ISO 15787:2010-01 (= ISO 15787:2001); E DIN ISO 15787:2017-12 zurückgezogen | [DIN Media](https://www.dinmedia.de/de/norm/din-iso-15787/290821467); [din.de](https://www.din.de/en/wdc-beuth:din21:290821467) (Suchauszug) | A | keine EN-Übernahme gefunden, also „DIN ISO“, nicht „DIN EN ISO“ |
| ISO 15787:2016 | 2. Ausgabe, veröffentlicht 08/2016, 33 S. (EN) | Stufe 90.93 „bestätigt“ am 29.10.2024; ersetzt ISO 15787:2001 | [genorma](https://genorma.com/en/standards/iso-15787-2016); [BSI](https://knowledge.bsigroup.com/products/technical-product-documentation-heat-treated-ferrous-parts-presentation-and-indications) (Suchauszug „Current“) | A | keine Revision in Arbeit gefunden |
| DIN 6773 (alte Härteangabe) | zurückgezogen | DIN ISO 15787 (2001er Basis) beruht auf DIN 6773:2001-04 | DIN Media 15787:2001 (Suchauszug); [Arnold-Horsch-Wiki](https://wiki.arnold-horsch.de/index.php/Normgerechte_W%C3%A4rmebehandlungsangaben_und_Pr%C3%BCfvorschriften_erstellen) („Vorgänger DIN 6773 Teil 1–5“) | A | Lehrseiten (maschinenbau-wissen, technisches-zeichnen.net) zitieren noch „DIN 6773 bis 6775“ |
| ISO 18203 (Bestimmung der Dicke gehärteter Randschichten: CHD, SHD, NHD) | **DIN EN ISO 18203:2026-05** (ISO 18203:2026), 22 S. | ersetzt DIN EN ISO 18203:2022-07. Änderungen: Verweis auf Kugelstrahlen und **Verbindungsschichtdicke CLT entfernt**, Standard-Prüflasten für Härtetiefen ergänzt, Rockwell-Verfahren in Tabellen, Kernhärteprüfung präzisiert | [DIN Media](https://www.dinmedia.de/de/norm/din-en-iso-18203/400150378) | B | Prüfnorm, nicht Zeichnungsnorm. Dass ISO 18203 ISO 2639/3754/4970 ersetzt, wurde nicht bestätigt (C) |
| ISO 2081 (galvanische Zinküberzüge auf Eisen/Stahl) | ISO 2081:2018 / EN ISO 2081:2018 | ersetzt ISO 2081:2008. Ein BSI-Suchauszug nennt auch 2018 „withdrawn“ (unbestätigt) | [genorma EN ISO 2081:2018](https://genorma.com/en/standards/en-iso-2081-2018); [din.de ISO 2081](https://6sku3uaup9f9.din.de/en/standard/iso-2081/287080785) (Suchauszüge) | B | DE-Ausgabe (DIN EN ISO 2081:2018-?) nicht bestätigt |
| ISO 19598 (Zink und Zinklegierungen, Cr(VI)-frei nachbehandelt) | **DIN EN ISO 19598:2017-04** (EN ISO 19598:2016) | ersetzt **DIN 50979:2008-07** (zurückgezogen) | [DIN Media 19598](https://www.dinmedia.de/de/norm/din-en-iso-19598/255107122); [DIN Media 50979](https://www.dinmedia.de/de/norm/din-50979/107376629) (Suchauszüge) | B | Für neue Zeichnungen ist das die naheliegende Zinknorm (Cr(VI)-frei) |
| ISO 7599 (Anodisieren, dekorativ und schützend) | ISO 7599:2018 / EN ISO 7599:2018 | ersetzt ISO 7599:2010; 2023 bestätigt; **gilt nicht für Hartanodisieren** (dafür ISO 10074) | [ISO committee 70156](https://committee.iso.org/standard/70156.html); [BSI](https://knowledge.bsigroup.com/products/anodizing-of-aluminium-and-its-alloys-general-specifications-for-anodic-oxidation-coatings-on-aluminium) (Suchauszüge) | B | DE-Ausgabe DIN EN ISO 7599:2018-? nicht bestätigt |
| DIN 17611 (anodisch oxidierte Erzeugnisse aus Al, TLB) | **DIN 17611:2022-08** | ersetzt DIN 17611:2011-11 | [din.de](https://6sku3uaup9f9.din.de/en/standard/din-17611/355713766); [ANSI](https://webstore.ansi.org/standards/din/din176112022) (Suchauszüge) | B | Liefernorm für eloxierte Halbzeuge; Kurzzeichen E0…E6, EV1 … |
| DIN 50938 (Brünieren von Bauteilen aus Eisenwerkstoffen) | **DIN 50938:2025-06** | ersetzt DIN 50938:2018-01; Entwurf 2024-10 zurückgezogen; gilt **nicht** für Verbindungselemente und Halbzeuge | [DIN Media](https://www.dinmedia.de/de/norm/din-50938/390664734) (Suchauszug) | B | – |
| EN 10058 (warmgewalzte Flachstäbe, Maße, Grenzabmaße) | **DIN EN 10058:2019-02** | ersetzte 2004 DIN 1017; Flachstab bis Breite 150 mm, darüber Breitflachstahl | [Wikipedia DE Flachstahl](https://de.wikipedia.org/wiki/Flachstahl); TU Dortmund (Suchauszug, PDF) | A | – |
| EN 10060 (warmgewalzte Rundstäbe) | DIN EN 10060:2004-02 | – | – | C, unbelegt | Ausgabe aus Hintergrundwissen |
| EN 10278 (Blankstahl, Maße und Grenzabmaße) | **DIN EN 10278:2024-01** (EN 10278:2023), 14 S. | ersetzt 1999-12. **Unlegierte und legierte Stähle nach EN 10277 sind nicht mehr enthalten**, nur noch nichtrostende und besondere Stähle (Werkzeug-, Wälzlagerstahl) | [DIN Media](https://www.dinmedia.de/de/norm/din-en-10278/362672989); [iTeh EN 10278:2023](https://standards.iteh.ai/catalog/standards/cen/819adfdd-4ad0-432d-a32a-7a18c17d0fbe/en-10278-2023) (Suchauszug) | A | „Rund EN 10278 – 20 h9 – C45+C“ ist damit veraltet |
| EN 10277 → ISO 683-7 (Blankstahl, TLB) | **DIN EN ISO 683-7:2025-02** (ISO 683-7:2023) „Blankstahlerzeugnisse aus unlegierten und legierten Stählen“ | ersetzt DIN EN 10277:2018-09; enthält Abschnitt „Form, Maße und Grenzabmaße“ | [DIN Media](https://dinmedia.de/en/standard/din-en-iso-683-7/385094700) (gelesen: nur Titel); Ersatzvermerk nur Suchauszug | B | wo die Maßtoleranzen für C45+C jetzt genau stehen, ist offen |
| EN 755 / EN 754 (Al-Stangen stranggepresst / gezogen) | DIN EN 755-5:2008-06 (Rechteckstangen, Grenzabmaße); EN 754-5 (gezogen); -2 je mechanische Eigenschaften; -3 Rundstangen | – | [beuth/din EN 755-5](https://www.beuth.de/en/standard/din-en-755-5/102909580); [DIN Media EN 754-5](https://www.dinmedia.de/en/standard/din-en-754-5/102910065) (Suchauszüge) | B | Ausgaben von 754-x/755-2/-3 nicht geprüft |

## 2. Wärmebehandlung (DIN ISO 15787)

| Regel | Wert/Bedingung | Quelle (URL) | Beleg | Hinweis |
|---|---|---|---|---|
| Inhalt der Norm | Darstellung und Angabe des **Endzustands** wärmebehandelter Teile aus Eisenwerkstoffen | [DIN Media](https://www.dinmedia.de/de/norm/din-iso-15787/290821467); [genorma](https://genorma.com/en/standards/iso-15787-2016) | A | nur Eisenwerkstoffe; Al-Aushärten u. Ä. nicht erfasst |
| Neu in 2018-08 gegenüber 2010-01 | Angaben für den Zustand nach der Wärmebehandlung (vor Fertigbearbeitung) **und** nach Fertigbearbeitung; Beispiele für Härtewerte mit Toleranzen; Linienarten für örtliche Bereiche, **neu eine breite Punktlinie für Bereiche, die nicht wärmebehandelt werden dürfen**; Bildzeichen in Anhang A, Tabellen aus Anhang A entfernt; neu: Weichfleckigkeit, örtliche Bereiche, Oxidschichtdicke, Wärmebehandlungsanweisung (HTO) und -plan (HTD); Randschichtschmelzhärten entfallen | [DIN Media](https://www.dinmedia.de/de/norm/din-iso-15787/290821467) | B | laut DIN Media Tabellen aus Anhang A entfernt; ob die Tabellen A.4–A.10 (Grenzhärten, Stufungen), auf die das Wiki verweist, betroffen sind, ist nicht belegt |
| Wortangabe des Zustands | z. B. „gehärtet“, „gehärtet und angelassen“, „vergütet“, „einsatzgehärtet (und angelassen)“, „randschichtgehärtet“, „nitriert“, „nitrocarburiert“, „geglüht“ (mit Kurzzeichen nach ISO 4885, z. B. +A, +N) | [Arnold-Horsch-Wiki](https://wiki.arnold-horsch.de/index.php/Normgerechte_W%C3%A4rmebehandlungsangaben_und_Pr%C3%BCfvorschriften_erstellen); [ingenieurkurse](https://www.ingenieurkurse.de/technische-darstellungen-maschienenbau/unterschiedliche-schweisssymbolsysteme/bemassen-der-schweissnaht/was-kann-nach-der-gabel-stehen.html) (Suchauszug); [maschinenbau-wissen](https://www.maschinenbau-wissen.de/skript3/konstrkution-entwicklung/technisches-zeichnen/173-haerte) | A | „gehärtet“ allein nur ohne Anlassen (Wiki, B) |
| Mehrere Behandlungen | in der Reihenfolge der Durchführung nennen | Arnold-Horsch-Wiki | B | Liste `behandlung` muss geordnet sein |
| Härte allein genügt nicht | Verfahren/Zustand und Härtewert angeben; Prozessparameter nur, wenn vorgeschrieben (Verantwortung geht dann auf den Besteller über), sonst in HTO/HTD | Arnold-Horsch-Wiki | B | swki gibt nur Ergebnisse an |
| Härtewert mit Prüfverfahren | Kurzzeichen HRC (ISO 6508-1), HV (ISO 6507-1), HBW (ISO 6506-1), bei HV/HBW mit Prüfkraft, z. B. „HV 10“, „HBW 2,5/187,5“ | Arnold-Horsch-Wiki; [technisches-zeichnen.net](https://www.technisches-zeichnen.net/technisches-zeichnen/grundkurs-02/hearteangaben.php); maschinenbau-wissen | A | – |
| Jeder Härtewert mit Toleranz | Toleranz so groß, wie die Funktion zulässt | Arnold-Horsch-Wiki; iTeh-Musterauszug ISO 15787:2016 (Suchauszug) | A | – |
| Schreibweise alt (DIN 6773 / DIN ISO 15787:2010) | einseitige Plustoleranz ohne Klammern: „gehärtet und angelassen 58+4 HRC“, „700+150 HV 10“, „gehärtet 40+2 HRC“ | Arnold-Horsch-Wiki; technisches-zeichnen.net; ingenieurkurse (Suchauszug) | A (für die alte Schreibweise) | weit verbreitet, aber nicht der Stil der Ausgabe 2018 |
| Schreibweise neu (ISO 15787:2016 / DIN ISO 15787:2018) | Härtewert mit Grenzabmaßen in Klammern, symmetrisch oder einseitig, z. B. „(62 ± 2) HRC“, „(64 0/−4) HRC“; laut Wiki „± statt einseitiger Plustoleranz“ | Arnold-Horsch-Wiki (Aussage zur Änderung); [iTeh-Musterauszug ISO 15787:2016](https://cdn.standards.iteh.ai/samples/56851/75b9af0b11f0441f963d64167ccbfd5a/ISO-15787-2016.pdf) (nur Suchauszug, PDF nicht geöffnet) | B (Notiz: zwei Quellen, aber Form nur aus Suchauszug) | genaue Typografie (Klammer, Hoch-/Tiefstellung, „0/−4“) mit dem Normtext klären |
| Mindesttoleranz (Erfahrungswert) | HRC ≥ +6, HV10 ≥ +150, HBW 2,5/187,5 ≥ +70, Rm ≥ +150 MPa; Begründung: Messunsicherheit frisst bei +4 HRC den Großteil | Arnold-Horsch-Wiki | B | Autorenmeinung, keine Norm; als `validieren`-Hinweis denkbar |
| Einsatzhärten: Kurzzeichen | CHD (Case Hardening Depth), früher Eht | Arnold-Horsch-Wiki; technisches-zeichnen.net („Eht“) | A | – |
| Einsatzhärten: Grenzhärte | im Regelfall 550 HV1 | Arnold-Horsch-Wiki; AWT-Hinweise zu DIN EN ISO 18203 (Suchauszug); [ZwickRoell](https://www.zwickroell.com/industries/metals/metals-standards/case-hardness-depth-chd-iso-2639/) (Suchauszug) | A | abweichende Grenzhärte als Index, z. B. „CHD 600HV3“ (Wiki, B) |
| Einsatzhärten: Schreibweise | alt: „einsatzgehärtet und angelassen 60+4 HRC, Eht = 0,8+0,4 mm“; Wiki: „CHD = 0,8 – 1,2 mm“, „CHD 1,0+0,3“, „CHD 600HV3 = 0,5 – 0,8 mm“ | [Merkblatt 452 Einsatzhärten](https://d-nb.info/1261039181/34) (Suchauszug); Arnold-Horsch-Wiki; [Techniker-Forum](https://www.techniker-forum.de/thema/haerte-auf-technische-zeichnungen.34936/) (Suchauszug) | A (Nennwert + Abmaß in mm) | Form nach 2016 („CHD = (0,8 +0,4/0) mm“?) C, unbelegt |
| CHD am Fertigteil oder vor Schleifen | eindeutig angeben, ob nach Wärmebehandlung oder am Fertigteil geprüft; Vorbearbeitungsmaße in eckigen Klammern oder Wortangabe „vor dem Schleifen“/„nach dem Schleifen“; Schleifaufmaß mindert CHD | Arnold-Horsch-Wiki; DIN Media (Änderung 2018: beide Zustände) | A | Feld `zustand` nötig, sobald ein Feature `bearbeitung: schleifen` die behandelte Fläche trifft |
| Aufkohlungstiefe CD | nur, wenn nicht direkt nach dem Aufkohlen gehärtet wird (Zwischenbearbeitung); Index für Grenzmerkmal, z. B. CD0,35 | Arnold-Horsch-Wiki | B | selten; nicht ins erste Schema |
| Randschichthärten: SHD | Grenzhärte im Regelfall 80 % der Mindest-Oberflächenhärte (in HV); Beispiel „600 – 750 HV 30, SHD 500 = 0,8 – 1,6 mm“; Verfahren (induktiv, Flamme) nur, wenn vorgeschrieben | Arnold-Horsch-Wiki; AWT-Hinweise (Suchauszug, 80 % der Oberflächen-Mindesthärte) | B (Widerspruch, s. u.) | – |
| Nitrieren: NHD | Grenzhärte im Regelfall Kernhärte + 50 HV0,5; abweichende Prüflast angeben; Beispiele „≥ 800 HV3, NHD HV0,3 = 0,1 – 0,15 mm“, „plasmanitriert ≥ 950 HV10, NHD = 0,3 – 0,4 mm“ | Arnold-Horsch-Wiki | B | – |
| Nitrocarburieren: CLT | Verbindungsschichtdicke in µm, z. B. „CLT = 12 – 18 µm“; Bestimmung nach DIN 30902 | Arnold-Horsch-Wiki | B | DIN EN ISO 18203:2026 nimmt CLT heraus (DIN Media). Wo CLT jetzt bestimmt wird, ist offen |
| Kernhärte | nur angeben, wenn eine Prüfung vorgeschrieben ist | [Arnold-Horsch-Wiki Prüfung](https://wiki.arnold-horsch.de/index.php/Pr%C3%BCfung_w%C3%A4rmebehandelter_Bauteile) (Suchauszug) | B | optionales Feld |
| Werkstoffangabe | Werkstoffnummer oder Normbezeichnung (1.7225 / 42CrMo4) mit Lieferzustand (z. B. +QT), keine Handelsnamen | Arnold-Horsch-Wiki | B | betrifft `material` und `halbzeug` |
| Örtliche Behandlung: Bereich | **breite Strichpunktlinie außerhalb der Kontur**, mit Maßen (Nennmaß, Toleranz) | Arnold-Horsch-Wiki (Typ 04.2.1); technisches-zeichnen.net; [maschinenbau-wissen](https://www.maschinenbau-wissen.de/skript3/konstrkution-entwicklung/technisches-zeichnen/173-haerte); ingenieurkurse (Suchauszug) | A | bei Drehteilen genügt eine Mantellinie (Wiki, B). Linientypnummer nach ISO 128-24 (zurückgezogen), heute ISO 128-2 |
| Übergangszone | liegt außerhalb des Nennmaßes der behandelten Länge | Arnold-Horsch-Wiki | B | – |
| „darf behandelt werden“ | breite Strichlinie (Typ 02.2.1), meist ohne Toleranz | Arnold-Horsch-Wiki (Stand 2010) | B | – |
| „darf nicht behandelt werden“ | 2010: schmale Zweipunktlinie (Typ 05.1); **2018: neu breite Punktlinie** | Arnold-Horsch-Wiki (2010); DIN Media (2018) | B (Widerspruch) | für 2018 gilt die Punktlinie. Lehrseiten: Vermerk „Abdecken“ unter der Härteangabe (maschinenbau-wissen) |
| Mehrere Bereiche | mit Kennzahlen markieren, Werte unter den Wortangaben je Kennzahl wiederholen | Arnold-Horsch-Wiki | B | passt auf `behandlung`-Einträge mit `id` |
| Messstellen | Bildzeichen (Pfeil nach Bild 1 der Norm), bei mehreren mit Kennzahl, Lage bemaßt; ohne Angabe wählt der Prüfer frei; alternativ mitbehandeltes Probestück | Arnold-Horsch-Wiki; Wiki-Beispiel „Messstelle 1 … 58 – 62 HRC, Messstelle 2 …“ (Suchauszug derselben Quelle) | B | im ersten Schema weglassen (C für das genaue Zeichen) |
| Wärmebehandlungsbild | vereinfachte, verkleinerte Zusatzdarstellung des Teils mit den Zonen, Titel „Wärmebehandlungsbild“ | Arnold-Horsch-Wiki; ingenieurkurse (Suchauszug) | A | für SolidWorks: zusätzliche Ansicht mit Skizzenlinien |
| Lage der Angabe | Wortangaben, Härte und Härtetiefe **in der Nähe des Schriftfelds**; Wärmebehandlungsbild „in der Nähe des Schriftfeldes“ | iTeh-Musterauszug ISO 15787:2016 (Suchauszug); ingenieurkurse (Suchauszug) | B (Widerspruch, s. u.) | passt zur Sammelangabe-Notiz der Design-Spec |
| Werkstofffeld des Schriftfelds | Behandlung im Schriftfeld neben dem Werkstoff | – | C, unbelegt | ISO 7200 kennt kein Pflichtfeld „Wärmebehandlung“; Firmenvorlage abwarten |

**Widersprüche:**
- **Toleranzschreibweise:** Wiki, Lehrseiten und Foren schreiben „58+4 HRC“ (einseitig, ohne Klammer). Für ISO 15787:2016 nennen
  das Wiki und der iTeh-Auszug Klammer und ± bzw. „0/−4“. Das Wiki bevorzugt ausdrücklich die alte Schreibweise. Beides ist in
  Umlauf, die Ausgabe 2018 ist die gültige.
- **80 %-Grenzhärte:** Das Wiki ordnet sie dem Randschichthärten (SHD) zu. Ein Suchauszug nennt sie im Zusammenhang mit der CHD
  bei Rockwell-Prüfung der Oberfläche. Für CHD bleibt 550 HV1 der Regelfall (A).
- **Linie „darf nicht behandelt werden“:** Wiki (2010) schmale Zweipunktlinie, DIN Media (2018) neue breite Punktlinie.
- **Lage:** Der ISO-Auszug nennt die Nähe des Schriftfelds. Das Wiki erlaubt das Wärmebehandlungsbild „an einer freien Stelle“.
- **Tabellen aus Anhang A:** Laut DIN Media wurden in der Ausgabe 2018 Tabellen aus Anhang A entfernt. Ob das die Tabellen
  A.4–A.10 (Grenzhärten, CHD-/NHD-Stufungen) betrifft, auf die das Wiki verweist, ist nicht belegt. Die Wiki-Werte sind darum
  für 2018 nicht gesichert.
- **Normbezug der Lehrseiten:** maschinenbau-wissen und technisches-zeichnen.net nennen „DIN 6773 bis 6775“, das ist veraltet.
  technisches-zeichnen.net nennt die örtliche Tiefe „Rht“ (vermutlich Randhärtetiefe, alt).

## 3. Oberflächenbehandlung und Beschichtung (nur Zeichnungsangabe)

| Regel | Wert/Bedingung | Quelle (URL) | Beleg | Hinweis |
|---|---|---|---|---|
| Zink ISO 2081: Aufbau | Grundwerkstoff / Zn + Mindestschichtdicke in µm / Chromatier- bzw. Passivierkennung / ggf. Nachbehandlung T…; **einfacher Schrägstrich**, z. B. „Fe/Zn15/B“, „Fe/Zn8/C“; englischer Vorsatz „Electrodeposited coating ISO 2081 – …“ | [Modulus Metal](https://www.modulusmetal.com/2024/11/06/iso-2081-designation/); [Ramo](https://ramo.se/en/technical-information/surface-treatment-codes/) | A (Aufbau, einfacher Strich); Vorsatz B; deutscher Vorsatz „Galvanischer Überzug ISO 2081 – …“: C, unbelegt | Ausgabe der Quellen nicht genannt |
| Zink ISO 2081: Kennbuchstaben | Modulus: A transparent, B gelb, C „clear chromate“, D blau; Ramo: A blau, C gelb, D grün, F schwarz | Modulus Metal; Ramo | B (Widerspruch) | Buchstaben je Ausgabe verschieden; nicht ohne Normtext verwenden |
| Wasserstoffversprödung ISO 2081 | Wärmebehandlung vor (SR) bzw. nach (ER) dem Beschichten in der Bezeichnung, z. B. „Fe/SR(250)≥3/Zn10/ER(200)10/D/T3“ | Modulus Metal | B | nur bei hochfesten Teilen; nicht ins erste Schema |
| Zink/Zinklegierung ISO 19598 (früher DIN 50979) | **Doppelschrägstrich**: Grundwerkstoff // Überzug + Schichtdicke // Passivierung // Nachbehandlung, z. B. „Fe//Zn8//Cn//T0“, „Fe//ZnNi8//Fn//T2“, „Fe//ZnFe12//Cn//T0“ | Ramo (DIN-50979-Spalte); Modulus Metal Vergleich DIN 50979/ISO 19598/ISO 2081 (Suchauszug); DIN-Media-Suchauszug zu ISO 19598 („Fe//ZnNi8//Cn//T0“) | A | Vorsatz z. B. „Galvanischer Überzug DIN EN ISO 19598 – …“ (C für den genauen Vorsatz) |
| Passivierung/Nachbehandlung ISO 19598 | An = transparent (dünnschicht), Cn = irisierend (dickschicht), Fn = schwarz; T0 = ohne, T2 = Versiegelung | Ramo; Modulus Metal (Suchauszug) | A | Ramo-Tabelle hat Tippfehler („FE//Zb8“, An zweimal) |
| Eloxal DIN 17611: Kurzzeichen | Vorbehandlung E0 (entfetten, desoxidieren) … E6 (beizen); Farbe EV1 = natur (farblos), C-0 = natur (Hydro), C31/C32 Bronzetöne; z. B. „E6/EV1 nach DIN 17611“ | Heinze/HD Wahl, Modulor, Hydro (alle Suchauszüge) | B | – |
| Eloxal: Schichtdicke | Klassen in µm: 10, 15, 20, 25; „Klasse 20 nach DIN 17611“; 5 µm entspricht nicht DIN 17611 | Hydro Rackwitz, Gutmann (Suchauszüge) | B | ISO 7599: Kennzeichnung der Klassen (AA…) nicht belegt |
| Eloxal: Zeichnungswortlaut | z. B. „eloxiert DIN 17611 – E6/EV1 – 20 µm“ oder „anodisiert ISO 7599 – AA20 – E6 natur“ | – | C, unbelegt | vom Suchwerkzeug abgeleitet, nicht aus einer Quelle; Hartanodisieren nach ISO 10074 gesondert |
| Brünieren | Angabe „brüniert DIN 50938“ (Norm gilt für Bauteile, nicht für Verbindungselemente und Halbzeuge) | [DIN Media](https://www.dinmedia.de/de/norm/din-50938/390664734) (Geltungsbereich, Suchauszug) | Wortlaut: C, unbelegt; Geltungsbereich: B | Brünieren ist kaum Korrosionsschutz; ggf. „brüniert und geölt“ (C) |
| Nitrocarburieren | ist Wärmebehandlung nach DIN ISO 15787: Wortangabe „nitrocarburiert“, Härte, NHD, ggf. CLT in µm | Arnold-Horsch-Wiki | B | gehört zu `behandlung`, nicht zu Beschichtungen |
| Beschichtung nur für Funktionsflächen | örtliche Beschichtung bzw. Abdeckung mit breiter Strichpunktlinie wie Wärmebehandlung | – | C, unbelegt | für Beschichtungen keine Quelle gefunden |

**Widersprüche:**
- **„Fe//Zn8//C“ aus der Aufgabe gibt es so nicht.** Es mischt den Doppelstrich von ISO 19598 mit einem Kennbuchstaben nach
  ISO 2081. Richtig ist „Fe/Zn8/C“ (ISO 2081) oder „Fe//Zn8//Cn//T0“ (ISO 19598).
- Die Bedeutung der ISO-2081-Kennbuchstaben (A/B/C/D/F) ist zwischen Modulus Metal und Ramo verschieden.
- Ein BSI-Suchauszug meldet ISO 2081:2018 als „withdrawn“. Andere Auszüge führen sie als aktuell. Nicht geklärt.

## 4. Halbzeug und rohe Flächen

| Regel | Wert/Bedingung | Quelle (URL) | Beleg | Hinweis |
|---|---|---|---|---|
| Flachstab warmgewalzt | Bezeichnung: Erzeugnis, Norm, Breite × Dicke × Länge, Längenart (M/F/E), Werkstoffnorm, Stahlsorte, z. B. „Flachstab EN 10058 – 30 x 6 x 6000 – M – Stahl EN 10025 – S235JR“ | [TU Dortmund, Tabelle Halbzeuge](https://lkp.mb.tu-dortmund.de/storages/me-mb/r/dokumente/Leseproben/b-tabelle-halbzeuge.pdf) (nur Suchauszug, PDF) | B | heute „EN 10025-2“ (Suchauszug, B) |
| Flachstab vs. Breitflachstahl | Flachstab bis Breite 150 mm; > 150 mm Breitflachstahl; ab 300 mm Blech; < 5 mm Dicke Bandstahl | [Wikipedia DE](https://de.wikipedia.org/wiki/Flachstahl); [bauforumstahl](https://archiv.bauforumstahl.de/fileadmin/user_upload/bauforumstahl.de/wissen/arbeitshilfen/Arbeitshilfen-Stahlbau/2020-06-03_SA_10.7_Erzeugnistoleranzen_fuer_warmgewalzte_Flachstaebe.pdf) (Suchauszug, PDF) | A | `validieren` kann `art: flach` gegen Breite prüfen |
| Rundstab warmgewalzt | „Rundstab EN 10060 – 19,70 x 3000 F – P – Stahl EN 10025 – S235JR“ | TU Dortmund (Suchauszug) | B | – |
| Blankstahl (alt) | „Rund EN 10278 – 30 h9 x Lager 6000 – EN 10277-3 – 38SMn2“; Zustände +C gezogen, +SH geschält, +SL geschliffen, +PL poliert; h9 typisch für gezogen/geschält | TU Dortmund (Suchauszug); Kindlimann, WS Stahl (Suchauszüge, h9) | B | **veraltet**: EN 10278:2023 deckt Stähle nach EN 10277 nicht mehr ab, EN 10277 ist nicht mehr mehrteilig |
| Blankstahl (neu) | unlegiert/legiert nach DIN EN ISO 683-7:2025-02; nichtrostend/besonders nach DIN EN 10278:2024-01 | DIN Media (s. Kap. 1) | A (EN 10278 eingeschränkt), B (ISO 683-7) | Bezeichnungsmuster nach ISO 683-7 nicht gefunden: C |
| Al-Rechteckstange | stranggepresst: Grenzabmaße EN 755-5, Eigenschaften EN 755-2; gezogen: EN 754-5 bzw. EN 754-2; Werkstoff „EN AW-6082 T6“ | metallservice.ch Datenblatt (Suchauszug); beuth/DIN Media (Suchauszüge) | B | Zustand (T6, T651) gehört zum Werkstoff |
| Al-Rundstange | stranggepresst EN 755-3, gezogen EN 754-3 | metallservice.ch (Suchauszug) | B | – |
| Al-Bezeichnungssyntax | z. B. „Rechteckstange EN 755-5 – EN AW-6082 T6 – 50 x 10“ | – | C, unbelegt | Reihenfolge nicht belegt |
| Präzisionsplatte (gefräst/gewalzt, z. B. EN AW-5083 gegossen, beidseitig feingefräst) | Toleranzen und Ebenheit nach Herstellerdatenblatt; keine EN-Maßnorm gefunden | – | C, unbelegt | `norm` frei lassen, `hersteller`/Handelsname vermeiden (Werkstoffangabe B) |
| Symbol „Materialabtrag nicht zulässig“ | Kreis im Wurzelzeichen (ISO 1302); Gegenstück: Querstrich = Materialabtrag gefordert | [Digital Surf Guide](https://guide.digitalsurf.com/en/guide-indications-iso-1302.html); HAW-Hamburg-Rauheitsposter (Suchauszug, DIN EN ISO 1302:2002); [Wevolver](https://www.wevolver.com/article/surface-finish-symbols-how-to-read-a-drawing-callout) (Suchauszug) | A (ISO 1302) | Form in ISO 21920-1 (mit Strich am Dreieck): C. Der Kreis heißt „kein Abtrag“, nicht ausdrücklich „wie Halbzeug“ |
| Sammelangabe mit Ausnahme in Klammern | z. B. „√Ra 3,2 (◯)“ neben dem Schriftfeld: alle Flächen Ra 3,2 außer den mit Kreis gekennzeichneten | – | C, unbelegt | in `recherche.md` Kap. 6 ebenfalls C |
| Vermerk „Rohmaß“ / „Halbzeugoberfläche“ / „Flächen ohne Angabe wie Halbzeug“ | Textnotiz statt oder neben dem Symbol | – | C, unbelegt | Firmenvorlage abwarten |
| Halbzeug auf der Zeichnung | Bezeichnung im Schriftfeld (Werkstoff/Rohteil) oder in der Stückliste; Länge als Zuschnittmaß | – | C, unbelegt | ISO 7200 hat kein Pflichtfeld „Halbzeug“ |

**Widersprüche:**
- Die TU-Dortmund-Beispiele und viele Händlerseiten bezeichnen Blankstahl nach „EN 10278 / EN 10277-x“. Seit DIN EN 10278:2024-01
  und DIN EN ISO 683-7:2025-02 ist das für unlegierten und legierten Stahl veraltet. Bestandszeichnungen bleiben gültig.
- Wikipedia nennt EN 10058 „seit 2004“ mit Ausgabe Februar 2019, ein Suchauszug nennt DIN EN 10058:2019-02. Das stimmt überein,
  die frühere Ausgabe war 2004-02.

## 5. Vorschlag für die Spec-Felder

Abgestimmt mit Design-Spec Abschnitt 4.1 und Plan Z1 Task 3 (Feature-Feld `behandlung: <String>`, Testfälle
`{"art": "bruenieren"}`, `{"art": "flach", "norm": "EN 10058", "masse": "100 x 20"}`). Die Vorschläge bleiben dazu kompatibel.

```yaml
behandlung:                       # Liste, Reihenfolge = Reihenfolge der Durchführung
  - art: einsatzhaerten           # Pflicht, Enum (s. u.)
    id: zone1                     # optional; Pflicht, wenn zwei Einträge dieselbe art haben
    haerte: {wert: 60, plus: 2, minus: 2, verfahren: HRC}   # optional; verfahren: HRC | HV10 | HV1 | HBW 2,5/187,5 …
    tiefe: {art: CHD, wert: 0.8, plus: 0.4, minus: 0, einheit: mm, grenzhaerte: "550 HV1"}   # grenzhaerte optional
    kernhaerte: {wert: 35, plus: 5, minus: 0, verfahren: HRC}  # optional
    zustand: fertigteil           # fertigteil | vor_schleifen (Default fertigteil)
  - art: verzinken
    schicht: {norm: "DIN EN ISO 19598", bezeichnung: "Fe//Zn8//Cn//T0"}
  - art: eloxieren
    schicht: {norm: "DIN 17611", bezeichnung: "E6/EV1", dicke_um: 20}

features:
  - id: lauf
    typ: …
    behandlung: zone1             # verweist auf id, sonst auf art (eindeutig)

halbzeug:
  art: flach                      # flach | rund | vierkant | sechskant | platte | rohr | blech
  norm: "EN 10058"                # Text, kein Enum; Ausgaben als Daten (Tabelle), nicht im Code
  masse: "50 x 10"                # mm, Querschnitt wie in der Normbezeichnung; Länge aus Hüllquader + Zugabe
  toleranz: h9                    # optional, Blankstahl
  zustand: "+C"                   # optional, Lieferzustand (+C, +SH, +SL; Al: T6 steht in material)
```

**Enum `art`:** `haerten` (nur ohne Anlassen, Wortangabe „gehärtet“), `haerten_anlassen`, `vergueten`, `einsatzhaerten`, `randschichthaerten`, `nitrieren`, `nitrocarburieren`,
`gluehen`, `eloxieren`, `hartanodisieren`, `verzinken`, `bruenieren`, `beschichten` (freier `schicht.bezeichnung`-Text mit
`norm`). Das Beispiel der Aufgabe hatte kein `vergueten`, `randschichthaerten`, `nitrocarburieren`, obwohl die Norm sie
unterscheidet. `tiefe.art`: `CHD`, `SHD`, `NHD`, `CLT` (CLT in µm, die anderen in mm).

**Bedeutung von `wert`/`plus`/`minus`** (für `haerte`, `kernhaerte`, `tiefe`):
- `plus` und `minus` gesetzt: Nennwert mit Grenzabmaßen. Wie das gedruckt wird, regelt `haertestil` (s. u.) für Härte **und**
  Tiefe: `iso15787_2016` → „(60 ± 2) HRC“ bzw. „CHD = (0,8 +0,4/0) mm“; `din6773` → „58+4 HRC“ bzw. „CHD = 0,8+0,4 mm“.
- `plus` weggelassen: Mindestwert, gedruckt „≥ 800 HV 3“.
- Statt Abmaßen darf auch ein Bereich stehen: `{von: 0.1, bis: 0.15}` → „NHD = 0,1 – 0,15 mm“. Das Wiki nutzt für NHD, SHD
  und CLT durchgehend Bereiche (B). Intern rechnet swki Bereich und Abmaße ineinander um.

**Begründung:**
- **`haerte` strukturiert statt als Text.** Die Schreibweise hängt von der Normausgabe ab (Kap. 2, Widerspruch). Mit Wert und
  Abmaßen erzeugt swki beide Stile. Die Wahl ist eine Hausregel in `config/standard.yaml`, z. B.
  `zeichnung.haertestil: iso15787_2016 | din6773`, mit `iso15787_2016` als Vorschlag. `validieren` kann prüfen, dass `plus` +
  `minus` > 0 ist, und einen Hinweis geben, wenn die Spanne unter dem Erfahrungswert liegt (HRC < 6; B, Hausregel).
- **`id` optional.** Der Verweis über `art` reicht für ein Teil mit einer Zone. Zwei Zonen gleicher `art` mit verschiedenen
  Werten (Kap. 2, „Mehrere Bereiche mit Kennzahlen“) brauchen sonst einen Namen. Feature-`behandlung` löst zuerst `id`, dann
  `art` auf. Bei Mehrdeutigkeit meldet `validieren` einen Fehler. Der bisherige Plan-Test (Feature-`behandlung` ohne gleichnamige
  `art`) bleibt gültig.
- **Kein Feld `flaechen`.** Örtlich gilt ein Eintrag genau dann, wenn mindestens ein Feature auf ihn verweist, sonst gilt er für
  das ganze Teil. Das ist eine Quelle statt zwei. Die Zeichnung setzt dann die breite Strichpunktlinie an die Flächen dieser
  Features (A) und die Kennzahl an die Linie.
- **`zustand`** wird nötig, sobald eine behandelte Fläche geschliffen wird (`bearbeitung: schleifen`): CHD vor dem Schleifen
  mit Aufmaß (A). `validieren` meldet einen Hinweis, wenn beides zusammentrifft und `zustand` fehlt.
- **`schicht.bezeichnung` als Text mit Normangabe.** Die Kurzzeichensysteme (ISO 2081 vs. ISO 19598, DIN 17611 vs. ISO 7599)
  sind zu verschieden für ein gemeinsames Schema. Ein Muster-Check je Norm ist trotzdem möglich: Regex für `Fe//…//…//T\d`.
- **`halbzeug.werkstoff` entfällt.** Der Werkstoff kommt aus `material`. Damit gibt es keine zweite Werkstoffquelle. Nur der
  Lieferzustand (`zustand`, `toleranz`) ist halbzeugspezifisch.
- **`masse` als Text** wie im Plan, aber mit festem Muster (`^\d+(,\d+)?( x \d+(,\d+)?)*$`, Dezimalkomma). swki zerlegt ihn,
  prüft ihn gegen den Hüllquader und ermittelt daraus die rohen Flächen (Design-Spec 4.1).
- **`norm` frei, Ausgaben in Daten.** Die Ausgabe wird nicht in die Spec geschrieben, die Zeichnung druckt die Norm undatiert
  oder mit Jahr aus einer Normentabelle. Hinweis aus Kap. 4: `validieren` warnt bei `norm: "EN 10278"` mit unlegiertem
  `material` (veraltet).

**Wortlaut, den die Zeichnung erzeugen würde** (Sammelangabe in Schriftfeldnähe; Beleggrad des Musters in Klammern):

| Spec | Zeichnungstext | Beleg |
|---|---|---|
| `haerten_anlassen`, Härte 60 ± 2 HRC, Stil `iso15787_2016` | „gehärtet und angelassen (60 ± 2) HRC – DIN ISO 15787“ | B (Form), Normverweis C |
| dasselbe, Stil `din6773`, Härte 58 +4/0 | „gehärtet und angelassen 58+4 HRC“ | A (alte Schreibweise) |
| `einsatzhaerten`, 60 ± 2 HRC, CHD 0,8 +0,4/0 | „einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm“; Stil `din6773`: „… 60+4 HRC, CHD = 0,8+0,4 mm“ | Härte B, CHD-Form C (2016) bzw. A (alt) |
| dasselbe, örtlich (Feature verweist, `id: 1`) | Linie breite Strichpunktlinie an den Flächen mit Maß und Kennzahl „1“; Text „1: einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm“; übrige Flächen ohne Angabe | Linie A, Kennzahl B |
| `nitrieren`, ≥ 800 HV3 (`minus: 0`, `plus` leer), NHD 0,1 – 0,15 | „nitriert ≥ 800 HV 3, NHD = 0,1 – 0,15 mm“ | B |
| `nitrocarburieren`, CLT 12 – 18 µm | „nitrocarburiert, CLT = 12 – 18 µm“ | B |
| `verzinken`, ISO 19598 | „Galvanischer Überzug DIN EN ISO 19598 – Fe//Zn8//Cn//T0“ | Bezeichnung A, Vorsatz C |
| `eloxieren`, DIN 17611 | „eloxiert DIN 17611 – E6/EV1, Schichtdicke 20 µm“ | B (Kurzzeichen), Wortlaut C |
| `bruenieren` | „brüniert DIN 50938“ | C |
| `halbzeug` flach, EN 10058, 50 x 10, `material: S235JR` | „Halbzeug: Flachstab EN 10058 – 50 x 10 – S235JR“ | B (Muster ohne Länge und Längenart) |
| rohe Flächen | Sammelangabe „√Ra 3,2 (◯)“ plus Notiz „◯ = Halbzeugoberfläche, unbearbeitet“; alternativ Kreis-Symbol an jeder rohen Fläche | Symbol A (ISO 1302), Sammelangabe und Notiz C |

Jede erzeugte Zeile sollte intern den Beleggrad ihrer Regel tragen (z. B. im Prüfbericht), damit der Prüfer C-Wortlaut
erkennt und mit der Firmenvorlage abgleicht.

## Offene Fragen

- Genauer Wortlaut und Typografie der Härteangabe nach ISO 15787:2016 (Klammer, ±, „0/−4“, CHD-Form): PDF-Kandidat
  iTeh-Musterauszug oder Normkauf.
- Nutzerentscheidung: Härtestil `iso15787_2016` oder `din6773` (in der Firma üblich?).
- **„Darf nicht behandelt werden“ ist im Vorschlag nicht ausdrückbar.** Beispiel: ein Gewinde soll beim Einsatzhärten weich
  bleiben (Kap. 2: Punktlinie nach 2018 bzw. Vermerk „Abdecken“). Möglich wäre am Feature
  `behandlung: {ausnehmen: <id|art>}` oder ein Top-Level-Feld `ausgenommen: [feature-ids]` im Eintrag. Das ist noch nicht entschieden.
- Wo stehen nach DIN EN ISO 683-7 die Grenzabmaße für C45+C, und wie lautet die Bezeichnung?
- Zeichnungswortlaut für Eloxal, Brünieren und die rohen Flächen: Firmenvorlage bzw. Firmenstandard.
- Status ISO 2081:2018 (BSI „withdrawn“?) und die deutsche Ausgabe.

## PDF-Kandidaten (brauchen OK)

| Dokument | URL | Größe | Nutzen |
|---|---|---|---|
| ISO 15787:2016, Musterauszug (iTeh) | https://cdn.standards.iteh.ai/samples/56851/75b9af0b11f0441f963d64167ccbfd5a/ISO-15787-2016.pdf | unbekannt | erste Seiten der gültigen Norm: Härteschreibweise, Lage nahe Schriftfeld |
| ISO 15787:2001, Musterauszug (iTeh) | https://cdn.standards.iteh.ai/samples/27926/4af193221b404a70ba5e2c84d07ba0bc/ISO-15787-2001.pdf | unbekannt | Vergleich alte Schreibweise |
| ISO 15787:2001, Vorschau SIS | https://www.sis.se/api/document/preview/899395/ | unbekannt | **ohne .pdf-Endung, vermutlich PDF** |
| DIN ISO 15787:2018-08, Inhaltsverzeichnis | https://www.din.de/de/mitwirken/normenausschuesse/nwt/veroeffentlichungen/wdc-beuth:din21:290821467/toc-2858115/download | unbekannt | **ohne .pdf-Endung, vermutlich PDF**; Gliederung (5.4.3 Härtewert und Grenzabmaße, 5.8 Härtetiefe) |
| DIN ISO 15787:2010-01, Inhaltsverzeichnis | https://www.din.de/de/mitwirken/normenausschuesse/nwt/veroeffentlichungen/wdc-beuth:din21:122364177/toc-1554623/download | unbekannt | **vermutlich PDF** |
| AWT-Hinweise zur Anwendung von DIN EN ISO 18203 (2023-09-22) | https://www.awt-online.org/awt-wAssets/docs/publikationen/2023-09-22-AWT-Hinweise_Anwendung_DIN_EN_ISO_18203_final.pdf | unbekannt | Grenzhärten CHD/SHD, Verweis auf Tabelle A.4 |
| Leitfaden Härten (Härterei Gerster, Swissmem) | https://swissmem.ch/fileadmin/user_upload/ZMIS_Microsite/PDF/Haerterei_Gerster_AG/Leitfaden_Haerten.pdf | unbekannt | Praxisbeispiele Zeichnungsangaben |
| Merkblatt 452 Einsatzhärten (DNB) | https://d-nb.info/1261039181/34 | unbekannt | **ohne .pdf-Endung, vermutlich PDF**; Beispiel „Eht = 0,8+0,4 mm“ |
| TU Dortmund, Tabelle Halbzeuge (Leseprobe) | https://lkp.mb.tu-dortmund.de/storages/me-mb/r/dokumente/Leseproben/b-tabelle-halbzeuge.pdf | unbekannt | Bezeichnungsbeispiele Flach-, Rund-, Blankstahl |
| ISO 2081:2008, Musterauszug (iTeh) | https://cdn.standards.iteh.ai/samples/44331/355f14090a09438cbce1e78a47a7c4e5/ISO-2081-2008.pdf | unbekannt | Bezeichnungsschema ISO 2081 |
| Würth DINO Kapitel 5 Oberflächenschutz | https://www.wuerth-industrie.com/web/media/de/pictures/wuerthindustrie/technikportal/dinokapitel/Kapitel_05_DINO_techn_Teil.pdf | unbekannt | Kurzzeichen Zink/Zinklegierung |
| Dresselhaus, Überzüge Verbindungselemente | https://www.dresselhaus.de/fileadmin/user_upload/06_downloadbereich/allgemeine_infos/Ueberzuege_Verbindungselemente.pdf | unbekannt | Vergleich DIN 50979 / ISO 19598 / ISO 2081 |
| Ammon, Eloxalhinweis | https://www.ammon.de/ammon/wp-content/uploads/Eloxalhinweis.pdf | unbekannt | Eloxal-Angaben aus Fertigersicht |
| HAW Hamburg, Rauheitsposter | https://www.haw-hamburg.de/fileadmin/TI-MP/PDF/IWS/Vorlesungen_Labore/Oberfl%C3%A4chentechnik_OFT/Rauheitsposter/Rauheitsposter.pdf | unbekannt | Symbole Materialabtrag (ISO 1302) |

## Quellenverzeichnis

Gelesen (HTML):
- DIN Media, DIN ISO 15787:2018-08: https://www.dinmedia.de/de/norm/din-iso-15787/290821467
- genorma, ISO 15787:2016: https://genorma.com/en/standards/iso-15787-2016
- Arnold-Horsch-Wiki, Normgerechte Wärmebehandlungsangaben: https://wiki.arnold-horsch.de/index.php/Normgerechte_W%C3%A4rmebehandlungsangaben_und_Pr%C3%BCfvorschriften_erstellen
- maschinenbau-wissen.de, Härte: https://www.maschinenbau-wissen.de/skript3/konstrkution-entwicklung/technisches-zeichnen/173-haerte
- technisches-zeichnen.net, Härteangaben: https://www.technisches-zeichnen.net/technisches-zeichnen/grundkurs-02/hearteangaben.php
- DIN Media, DIN EN ISO 18203:2026-05: https://www.dinmedia.de/de/norm/din-en-iso-18203/400150378
- Modulus Metal, ISO 2081 Designation: https://www.modulusmetal.com/2024/11/06/iso-2081-designation/
- Ramo, Surface treatment codes: https://ramo.se/en/technical-information/surface-treatment-codes/
- DIN Media, DIN EN 10278:2024-01: https://www.dinmedia.de/de/norm/din-en-10278/362672989
- DIN Media, DIN EN ISO 683-7 (nur Titel): https://dinmedia.de/en/standard/din-en-iso-683-7/385094700
- Wikipedia DE, Flachstahl: https://de.wikipedia.org/wiki/Flachstahl
- Digital Surf, Indication of surface texture (ISO 1302): https://guide.digitalsurf.com/en/guide-indications-iso-1302.html

Nicht lesbar: iTeh-Katalog ISO 15787:2016 (JavaScript, nur Kopf), gwp-ag.com/615 (404).

Nur Suchauszüge (höchstens B): BSI, din.de, ingenieurkurse.de, Techniker-Forum, ZwickRoell, AWT, DIN Media (19598, 50979,
50938, 17611, 755-5, 754-5), ISO committee 70156, Heinze/HD Wahl, Modulor, Hydro, TU Dortmund, bauforumstahl, Kindlimann,
WS Stahl, metallservice.ch, HAW Hamburg, Wevolver, iTeh EN 10278:2023, Modulus Metal (Vergleich DIN 50979/ISO 19598).
