# Auftrag der /goal-Session: SolidWorks-KI schneller bei gleicher Präzision (BTP)

Stand 24.10.2026. Erstellt von der Audit-Sitzung „SW KI Tool Performance Audit“.

## Ziel

Score nach dem [Bewertungsbogen BTP](../superpowers/specs/2026-10-23-bewertungsbogen-design.md) **≥ 6,5** in
**höchstens 5 Umbauten**. Ausgangswert (Durchgang 0): siehe [ergebnisse.md](ergebnisse.md). Hauptziele Geschwindigkeit
und Präzision; Präzision darf nicht sinken (§5.1 des Bogens).

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
