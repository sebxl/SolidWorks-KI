# Inbetriebnahme auf einem Firmenrechner

Die Firmenrechner laufen mit SolidWorks 2026 und Vollversion (Nutzer 2026-10-31). Alles bisher Gemessene stammt von Rechner A mit
SW 2025 und Student-Lizenz; **unter SW 2026 ist swki noch nie gelaufen**. Eine Datei eines Kollegen aus SW 2026 kann Rechner A nicht
bearbeiten (`BESTAND_VERSION_NEUER`). Bestandsdateien lassen sich also nur auf einem Firmenrechner einsetzen und abnehmen.

Die Reihenfolge läuft vom Billigen zum Teuren. Scheitert ein Schritt, dort anhalten und den Befund festhalten, nicht nachbessern,
bevor die Ursache klar ist: Jeder Befund ist eine echte Abweichung zwischen den Jahren.

## Voraussetzungen

- SolidWorks 2026 mit **deutscher Oberfläche** (Feature- und Skizzennamen werden gelesen, z. B. `Skizze1`).
- Python ≥ 3.13, Git.
- Rund 15 GB freier Arbeitsspeicher für SolidWorks bei Bewegungen (Spitze Prüfstation 14,3 GB auf Rechner A).
- Das Repository ist **öffentlich**. Kollegen-Dateien, Kundendaten und deren Maße nie committen; Aufträge bleiben im Arbeitsstand.

## Schritte

Alle Befehle aus dem Repo-Wurzelordner. SolidWorks gehört während der Live-Schritte allein diesem Lauf.

**1. Einrichten**

```bash
git clone https://github.com/sebxl/SolidWorks-KI.git
```

```bash
powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1 -Jahr 2026
```

Belegt: Registry-Erkennung, Vorlagen, Materialdatenbank, API-Index aus der 2026er-Hilfe. Prüfen, ob `sw_jahr`, `vorlage_teil` und
`vorlage_baugruppe` stimmen:

```bash
.venv\Scripts\python.exe -m swki rechner zeigen
```

**2. Prüfen ohne SolidWorks**

```bash
.venv\Scripts\python.exe -m pytest
```

```bash
.venv\Scripts\python.exe -m swki api pruefe-code
```

`pruefe-code` läuft gegen den 2026er-Index. `max_jahr_compiler: 2025` bleibt: Der Code soll auf beiden Rechnern laufen.

**3. Muster erzeugen**

```bash
.venv\Scripts\python.exe -m werkzeuge.sw_neustart
```

```bash
.venv\Scripts\python.exe -m werkzeuge.bestand_muster
```

Legt die Muster nach `<arbeitsordner>/BESTAND-MUSTER/2026/`, nicht ins Git. Das ist der erste Bau unter SW 2026, rohe API ohne Compiler.
Das Werkzeug übernimmt nur Dateien, die nach dem Wiederöffnen fehlerfrei sind und in beiden Konfigurationen das Soll-Volumen
treffen. Sonst nennt es die `abweichungen`. Bricht es bei der Materialsuche ab, fehlt `1.0038` in der Materialdatenbank dieses Rechners.

**4. Bestandsdateien live**

```bash
.venv\Scripts\python.exe -m werkzeuge.live_frisch tests/live/test_live_bestand.py tests/referenz/test_bestand.py --zeit 900
```

Belegt die Messungen, auf denen das Paket steht: Datei-ID nach `Save3`, Differenz je Konfiguration, Bau ab der Kopie, Negativfälle,
die ganze Referenz Lagerdeckel. `test_aufnahme_musterteil` prüft auch `einheitensystem == 5`; scheitert nur das, liegt es an der
Teilevorlage dieses Rechners, nicht an swki.

**5. Gesamte Regression**

```bash
.venv\Scripts\python.exe -m werkzeuge.live_frisch tests/referenz --zeit 1500
```

Normteil- und Kaufteil-Cache gelten je SW-Jahr und bauen sich beim ersten Lauf neu, der dauert also länger. Der Motorhalter braucht die
Nanotec-STEP im Quellordner der `kaufteilbibliothek`. Fehlt sie, meldet er `KAUFTEIL_QUELLE_FEHLT` mit der Download-URL; Herunterladen
nur mit OK des Nutzers.

**6. Ergebnis festhalten**

In `docs/bestandsdateien/ergebnisse.md`: Jahr, Servicepack, Lizenztyp, Ergebnis je Schritt, Abweichungen. Erst danach `CLAUDE.md`
und `rechner.beispiel.yaml` anpassen. Die Muster im Git bleiben bei ihrem Jahr, solange Rechner A mitläuft: SW 2025 kann Dateien
aus SW 2026 nicht öffnen.

**7. Abnahme**

Sobald eine echte Kollegen-Datei da ist: Spec Bestandsdateien §14, Skill `aendern`. Damit ist Etappe 1 fertig.

## Noch nicht belegt

Das Werkzeug und die Umstellung der Tests liefen auf SW 2025, auch gegen frisch erzeugte statt eingecheckte Muster. Ob SW 2026 sich
an den Stellen gleich verhält, die die S18-Messungen betreffen, zeigen erst die Schritte 3 bis 5. Falls `swki api bauen` an der
2026er-Hilfe scheitert, geht Schritt 1 mit `-OhneApi` weiter, dann fehlt aber `swki api` für jede Korrektur.
