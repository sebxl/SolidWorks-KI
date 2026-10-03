---
name: normteile
description: Genormte Verbindungselemente (Schrauben, Muttern, Scheiben, Stifte) abrufen oder erstmals bauen lassen – immer über swki normteil, nie als STEP-Download oder freihändig konstruiert. Verwenden, wenn ein Teil, eine Baugruppe oder der Nutzer ein Normteil braucht oder eine neue Größe/Norm aufgenommen werden soll.
---

# Normteile

Genormte Teile kommen **immer** aus `swki normteil` (Spec `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`).
Herstellerdaten (STEP) nur für nicht genormte Kaufteile.

## Abrufen
`.venv\Scripts\python.exe -m swki normteil hole "<Norm>" <Größe>[x<Länge>] [--variante <v>]`
- Vorhanden und aktuell → Pfad (`gebaut: false`). Sonst baut swki das Teil, prüft es vollständig selbst und legt es ab.
- Verfügbar: ISO 4762, ISO 4032, ISO 7089, ISO 8734 (`swki normteil tabellen-pruefen` zeigt Anzahl der Größen und gesperrte).
- Stand 2026-10-02: Alle vier Normen sind mit Web-Recherche abgeglichen, keine Größe ist gesperrt. Werkstoff ISO 8734
  (Variante St): 1.2210 statt 1.3505 (1.3505 fehlt in der SW-Materialdatenbank).

## Einbaureferenzen (für Baugruppen)
Achse = Modell-Y, Auflage auf y = 0; Bezugsebenen haben die Normale +y.

| Norm | Körper | Referenzen |
|---|---|---|
| ISO 4762 | Kopf y 0…k, Schaft y < 0 | `EINBAU_ACHSE`, `EINBAU_EBENE` (Kopfunterseite) |
| ISO 4032 | y 0…m | `EINBAU_ACHSE`, `EINBAU_EBENE` (eine Auflagefläche; beide Seiten gleich) |
| ISO 7089 | y 0…h | `EINBAU_ACHSE`, `EINBAU_EBENE` (y = 0), `EINBAU_EBENE_2` (y = h, Gegenseite: Kopf/Mutter) |
| ISO 8734 | y 0…l | `EINBAU_ACHSE`, `EINBAU_EBENE_1` (y = 0), `EINBAU_EBENE_2` (y = l) |

## Fehlercodes
| Code | Vorgehen |
|---|---|
| `NORMLAENGE_UNGUELTIG` | Nächste Normlänge (`naechste`) vorschlagen, nicht still ändern |
| `NORMTEIL_UNBEKANNT`, `NORMVARIANTE_UNBEKANNT` | Vorhandene Größen/Varianten nennen; neue Größe → „Erweitern“ |
| `NORMTEIL_GESPERRT` | Grund nennen; Nutzer entscheidet den Wert (eine Frage, mit Empfehlung) |
| `NORMVORLAGE_UNGEPRUEFT` | `swki normteil muster "<Norm>"` → Prüfer-Agent (`subagent_type: pruefer`) mit Tabelle, `spec`, `pruefbericht`, Bildern → Urteil als rohes JSON in Datei → `swki normteil urteil "<Norm>" <datei> --vorlage-pruefsumme <x>` (`vorlage_pruefsumme` aus der Ausgabe von `swki normteil muster`) |
| `NORMTABELLE_UNGUELTIG` | Befunde beheben (Tabelle), nie Regeln aufweichen |
| `NORMTEIL_PRUEFUNG` | Fehler in Vorlage oder Tabelle – melden, Laufordner nennen; Sollwerte nie an Messwerte anpassen |

## Erweitern (neue Größe oder Norm)
1. Tabelle `swki/wissen/normteile/<norm>.yaml` ergänzen (Werte aus Normwissen, `status: gesperrt`).
2. Abgleich: ≥ 2 unabhängige recherchierte Quellen je Wert (Claudes Wissen zählt nicht); Widersprüche → gesperrt, Nutzer fragen.
   Rohdaten des Abgleichs liegen unter `docs/stufe3a/abgleich/` (je Norm `<norm>.a.json`, `<norm>.b.json`, für Längen zusätzlich
   `<norm>.laengen.<a|b>.json`) – neue Abgleiche dort ablegen.
3. Neue Norm: Bauvorlage `vorlagen/<norm>.yaml` (alle Maße als Ausdrücke, Einbaureferenzen `EINBAU_*`, `pruefung` misst jedes Tabellenmaß; Ausnahme: Fasen ohne eigene Messart – `p` bei ISO 4762, `c` bei ISO 8734, Kopffase `k/10` –
   werden nur über Volumen/Hülle geprüft), Unit-Tests (Volumen), Live-Test, Prüfer-Urteil.
   Berührt das Rotationsprofil die Achse, muss die Mittellinie an beiden Enden über das Profil hinausragen, sonst scheitert
   der Bau mit „Gleichungen: Code 1“ (Spike S11). Parameternamen dürfen sich nicht nur in Groß-/Kleinschreibung
   unterscheiden (SolidWorks-Gleichungen sind nicht case-sensitiv, z. B. `d`/`D`).
4. `swki normteil tabellen-pruefen` und `pytest` grün.
