"""Stand der Nachbesserungsschleife eines Auftrags: Läufe, offene Mängel, Empfehlung für den nächsten Schritt.

Dateien je Lauf im Auftragsordner (protokolle/):
  <spec>.lauf-<n>.protokoll.json     (swki bauen)
  <spec>.lauf-<n>.pruefbericht.json  (swki pruefen)
  <spec>.lauf-<n>.pruefer.json       (Urteil des Prüfer-Agenten, von Claude geschrieben:
                                      {"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]})

Regel „kein Fortschritt“: verglichen werden nur Läufe, die durchgebaut und geprüft sind (Prüfbericht und Prüfer-Urteil),
jeweils mit dem letzten solchen Lauf davor. Ein Bauabbruch (Protokollstatus "fehler") hat keine Mängelzahl (offen None)
und verbraucht nur einen der höchstens 1 + max_nachbesserungen Läufe.
"""

import json
import re
from pathlib import Path

from swki.auftrag import lauf_datei, protokoll_ordner
from swki.cli import SwkiFehler


def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


_URTEIL_FORM = '{"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]}'


def pruefe_urteil(urteil, pfad: Path) -> None:
    """Form des Prüfer-Urteils (vom Controller abgelegtes JSON des Prüfer-Agenten)."""
    maengel = urteil.get("maengel") if isinstance(urteil, dict) else None
    gueltig = (
        isinstance(urteil, dict) and isinstance(urteil.get("bestanden"), bool) and isinstance(maengel, list)
        and all(isinstance(m, dict) and isinstance(m.get("knoten"), list) and isinstance(m.get("beschreibung"), str)
                for m in maengel)
    )
    if not gueltig:
        fehler = SwkiFehler(f"{pfad.name}: kein gültiges Prüfer-Urteil – erwartet {_URTEIL_FORM}")
        fehler.daten = {"code": "PRUEFER_URTEIL_UNGUELTIG"}
        raise fehler


def lies_laeufe(spec_pfad: Path) -> list[dict]:
    muster = re.compile(rf"^{re.escape(spec_pfad.stem)}\.lauf-(\d+)\.protokoll\.json$")
    ordner = protokoll_ordner(spec_pfad)
    nummern = sorted(int(m.group(1)) for p in (ordner.iterdir() if ordner.is_dir() else ()) if (m := muster.match(p.name)))
    laeufe = []
    for n in nummern:
        protokoll = _lies(lauf_datei(spec_pfad, n, "protokoll"))
        bericht = _lies(lauf_datei(spec_pfad, n, "pruefbericht"))
        urteil = _lies(lauf_datei(spec_pfad, n, "pruefer"))
        if urteil is not None:
            pruefe_urteil(urteil, lauf_datei(spec_pfad, n, "pruefer"))
        bau_ok = protokoll["status"] == "ok"
        code_maengel = len(bericht["maengel"]) if bericht else None
        pruefer_maengel = len(urteil["maengel"]) if urteil else None
        offen = (code_maengel or 0) + (pruefer_maengel or 0) if bau_ok else None  # Bauabbruch: nicht zählbar
        laeufe.append({
            "lauf": n,
            "bau": protokoll["status"],
            "dauer_s": protokoll["dauer_s"],
            "code_maengel": code_maengel,
            "pruefer": "ausstehend" if urteil is None else ("bestanden" if urteil["bestanden"] else "maengel"),
            "pruefer_maengel": pruefer_maengel,
            "offen": offen,
            "vergleichbar": bau_ok and bericht is not None and urteil is not None,
            "bestanden": bau_ok and bericht is not None and bericht["bestanden"] and urteil is not None
            and urteil["bestanden"],
        })
    return laeufe


def max_laeufe(spec: dict, standard: dict, anweisung: int | None = None) -> int:
    """Erster Lauf + Nachbesserungen; Vorrang: Spezifikation > Anweisung im Chat > config/standard.yaml."""
    if spec.get("max_nachbesserungen") is not None:
        nachbesserungen = spec["max_nachbesserungen"]
    elif anweisung is not None:
        nachbesserungen = anweisung
    else:
        nachbesserungen = standard["max_nachbesserungen"]
    return 1 + nachbesserungen


def empfehlung(laeufe: list[dict], maximal: int) -> tuple[str, str]:
    if not laeufe:
        return "bauen", "Noch kein Lauf: swki bauen"
    letzter = laeufe[-1]
    if letzter["bau"] == "ok" and letzter["code_maengel"] is None:
        return "pruefen", f"Lauf {letzter['lauf']} prüfen: swki pruefen --lauf {letzter['lauf']}"
    if letzter["bau"] == "ok" and letzter["pruefer"] == "ausstehend":
        return "pruefer", f"Prüfer-Agent für Lauf {letzter['lauf']} starten und Urteil ablegen"
    if letzter["bestanden"]:
        return "bestanden", f"Lauf {letzter['lauf']} bestanden: Bericht schreiben"
    # Regel „kein Fortschritt“ (Nutzerentscheidung 2026-10-01, Option A): nur durchgebaute und geprüfte Läufe werden
    # verglichen, jeweils mit dem letzten solchen Lauf davor; ein Bauabbruch verbraucht nur einen Lauf.
    vorher = [lauf for lauf in laeufe[:-1] if lauf["vergleichbar"]]
    if letzter["vergleichbar"] and vorher and letzter["offen"] >= vorher[-1]["offen"]:
        return "stopp_kein_fortschritt", (
            f"Offene Mängel Lauf {vorher[-1]['lauf']} → Lauf {letzter['lauf']}: {vorher[-1]['offen']} → "
            f"{letzter['offen']}: kein Fortschritt, anhalten und Nutzer informieren"
        )
    if len(laeufe) >= maximal:
        return "stopp_max", f"{len(laeufe)} von {maximal} Läufen verbraucht: anhalten und Nutzer informieren"
    return "nachbessern", f"Bauweg ändern und neu bauen (Lauf {letzter['lauf'] + 1} von höchstens {maximal})"
