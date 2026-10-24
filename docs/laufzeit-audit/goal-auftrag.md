# Auftrag der /goal-Session: SolidWorks-KI schneller bei gleicher Präzision (BTP)

Stand 24.10.2026. Erstellt von der Audit-Sitzung „SW KI Tool Performance Audit“.

## Ziel

Score nach dem [Bewertungsbogen BTP](../superpowers/specs/2026-10-23-bewertungsbogen-design.md) **≥ 6,5** in
**höchstens 5 Umbauten**. **Ausgangswert Durchgang 0: 4,9** (Details [ergebnisse.md](ergebnisse.md)). Hauptziele
Geschwindigkeit und Präzision; Präzision darf nicht sinken (§5.1 des Bogens).

## Was Durchgang 0 zeigt (Startpunkt neben der Recherche)

- Teilscores: Zeit Teile 1,3 (258 s) · Stehlager 4,8 (343 s) · Prüfstation 5,0 (995 s) · Präzision erster Lauf 3,5
  (3 Fehlerpunkte) · Fallen 10 (6/6) · Aufwand 5,0 · Robustheit 0,0 (28,2 GB).
- **Konstruktionsreview** 23–109 s je Lauf (Teile 25–33 % der Zeit) – darf schlanker werden (Recherche O12), nicht
  entfallen.
- **Prüfstation:** Durchlauf 601 s; Prüfen ~300 s (Bewegungsprüfung, Recherche O1/O2), Verknüpfen 91 s (O3), Teile
  105 s (O5 Wiederverwenden), Modell 200 s, Review 105 s, Prüfer 65 s.
- **Speicher Prüfstation 27,5–28,2 GB beim Bauen** (Verknüpfen/Grundstellung) – vorher 14,3 GB; Ursache offen,
  Robustheit-Teilscore 0. Lohnt eine Untersuchung (5 % Gewicht, aber auch Betriebsrisiko).
- Fehlerpunkte: Bezug `u: mitte` gleicht Höhen eines Bohrungspaars an (Kamera, Bemaßungsbezug); falscher Messanker
  eines Prüfwerts (Zentrieraufnahme). Präzisionshebel: Skill-Hinweise bzw. Prüfwerte aus der Geometrie ableiten.
- Fallen stehen bei 10 – jede Prüfer-Änderung muss 6/6 und 0 Fehlalarme halten.

## Lehren aus der Einrichtung (unbedingt beachten)

- **Nie zwei SolidWorks-Arbeiten gleichzeitig** (Messlauf, Fallen bauen, Regression, Referenz). Fallen-*Prüfungen*
  brauchen kein SolidWorks und dürfen parallel zu einem Lauf laufen.
- Fallen-Prüfer schreiben ihr Urteil meist selbst; fehlt eine `urteil-*.json`, das zurückgemeldete JSON unverändert
  ablegen. Dateien, die Prüfer versehentlich anlegen, entfernen.
- Messdaten des Messstands vom 09.10. liegen unter `MESSSTAND/messstand-2026-10-09/` – nicht anfassen.
- Lange Befehle (Prüfstation-`durchlauf` ~10 min) wandern im Agenten in den Hintergrund; der Lauf meldet sich danach.

## Lies zuerst

1. Bogen `docs/superpowers/specs/2026-10-23-bewertungsbogen-design.md` – Score, Sperren, Entscheidung §5, Regeln §8.
2. Audit `docs/laufzeit-audit/2026-10-23-audit.md` – wo die Zeit hängt (mit Korrekturen §7).
3. Recherche `docs/laufzeit-audit/recherche.md` – Optimierungen O1–O14, Rangliste §5.2, empfohlene Reihenfolge §5.3
   (U1 Baugruppen-Latenz → U2 Teile wiederverwenden → U4 Prüf- und Agentenpaket → Reserve). U3 (Fast Mode) ist
   **gestrichen** (Nutzer: Fast Mode und effort des Hauptagenten nicht im Bogen).
4. Ergebnisse `docs/laufzeit-audit/ergebnisse.md` – Durchgang 0, Bezug, Diagnose je Aufgabe.
5. `CLAUDE.md`, Messstand-Spec `docs/superpowers/specs/2026-10-09-messstand-design.md`, `werkzeuge/messstand/`.

## Ablauf je Umbau n (1 … 5)

1. Branch `btp-umbau-<n>` ab `btp` (Worktree unter `.claude/worktrees/`). Optimierungen umsetzen – TDD, Unit-Tests
   grün, neue SolidWorks-API-Aufrufe vorher mit `swki api methode|enum` nachschlagen und `swki api pruefe-code`.
2. Live-Regression `tests/referenz` grün (`.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz`, SolidWorks
   offen; Bewegungen und Kaufteile je Test auf frischem SolidWorks).
3. Ändert der Umbau `swki pruefen`, das Prüfverfahren oder `pruefer.md`: Fallen mit dem neuen Stand neu bauen
   (`-m werkzeuge.messstand fallen bauen`).
4. Durchgang n messen (Muster unten), `-m werkzeuge.messstand btp <n> --vergleich <aktueller Stand>`.
5. Entscheidung nach Bogen §5.1 (besser → Merge `btp-umbau-<n>` nach `btp`; sonst verwerfen), Ergebnis-Tabelle,
   Teilscores, Begründung in `docs/laufzeit-audit/ergebnisse.md`.
6. Abbruch bei Score ≥ 6,5 oder nach Umbau 5.

## Durchgang messen (wie Durchgang 0)

Je Aufgabe nacheinander (nie zwei Läufe gleichzeitig mit SolidWorks): `durchlicht` 1 und 2, `kamera`,
`zentrieraufnahme`, `stehlager`, `pruefstation`:

1. `-m werkzeuge.messstand vorbereiten <n> <aufgabe> <nr> --commit <branch>` → gibt den Prompt aus (bei `pruefstation`
   baut es vorher den Ausgangslauf, ~15 min).
2. Konstruktions-Agent als Subagent (`subagent_type: claude`, Vordergrund) mit genau diesem Prompt; die Agent-ID merken.
3. `-m werkzeuge.messstand abschliessen <lauf> --agent <id>` (`--haenger 1` bei Hänger/ungeplantem Neustart;
   Wiederholung nach §5.1 mit `--wiederholung-von <lauf>`).
4. Fallen: `fallen auftraege <n> --commit <branch>`, je Auftrag ein unabhängiger `general-purpose`-Agent mit dem
   Prompt (nur Read/Glob), dessen JSON-Urteil unverändert in die Datei `urteil` schreiben; dann `fallen auswerten <n>`;
   unklare Urteile in `entscheid.json` entscheiden und begründen.
5. `btp <n> --vergleich <stand>`; Worktrees mit `aufraeumen <n>` entfernen.

## Regeln (Bogen §8, Nutzerentscheidungen 24.10.2026)

- Freigabe ohne Rückfrage nur in Messstand-Aufträgen (`MESS-*`, `MESSREF-*`, `MESSFALLE-*`).
- Prüfer darf nicht entfallen; schmaler/schneller nur, wenn die Fallen nicht schlechter werden.
- Konstruktionsreview läuft wie im Betrieb; schlanker (Modell, effort, Geltungsbereich) erlaubt, Abschaffen nicht.
- Fast Mode und effort des Hauptagenten nicht ändern.
- Keine Änderung an Konstruktionsregeln, Freigabe-Schutz, Prüfungen gegen die freigegebene Kopie oder Schwellen von
  `swki pruefen`; Prüfungen dürfen schneller, nicht schwächer werden (neue Prüfungen wie Einschraublänge sind erlaubt).
- Kein `git push`, kein Merge nach `main` – das entscheidet der Nutzer am Ende.
- SolidWorks bei ~4 GB Private Bytes oder vor Läufen mit Bewegungen selbst neu starten (`-m werkzeuge.sw_neustart`).

## Ergebnis

Am Ende: `docs/laufzeit-audit/ergebnisse.md` mit allen Durchgängen und einer Schlusszusammenfassung (Endstand, was
übernommen/verworfen wurde, warum, offene Hebel), Branch `btp` mit den übernommenen Umbauten (nicht gepusht).
