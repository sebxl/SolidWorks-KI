"""Live-Tests einzeln auf frischem SolidWorks (CLAUDE.md: Bewegungen, Kopplungen, Kaufteile „je Test auf frischem
SolidWorks“). Ergänzt tests/live_einzeln.py um den Neustart und die Speicherspitze je Test.

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.live_frisch <datei|ordner|test-id> … [--zeit 900]
            [--grenze-mb 3000] [--protokoll lauf.jsonl]
- Ohne --grenze-mb: Neustart vor jedem Test. Mit --grenze-mb: nur, wenn SolidWorks nicht läuft oder seine Private
  Bytes vor dem Test über der Grenze liegen. Scheitert ein Neustart (z. B. Dokumente offen), endet der Lauf (Exit 2).
- Je Test eine Zeile OK/FEHLER/ZEITLIMIT mit Dauer und Speicherspitze (Private Bytes, alle 0,5 s abgetastet);
  --protokoll hängt je Test ein JSON-Objekt an (mit den Fehlerzeilen „E …“ von pytest).
- Nach einem Zeitlimit wird SolidWorks neu gestartet und weitergemacht. Exit 1, wenn ein Test nicht OK war.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from swki.konfig import PROJEKT, lade_rechner
from swki.speicher import Spitzenmessung
from werkzeuge.sw_neustart import NeustartFehler, instanzen, neustart, sw_privat_mb

PYTEST = [sys.executable, "-m", "pytest", "-m", "sw", "-q", "-p", "no:cacheprovider"]


def test_ids(pfad: str) -> list[str]:
    if "::" in pfad:
        return [pfad]
    aus = subprocess.run(PYTEST + [pfad, "--collect-only"], cwd=PROJEKT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return [z.strip() for z in aus.splitlines() if "::" in z]


def lauf(test: str, zeit: int) -> tuple[str, list[str]]:
    try:
        p = subprocess.run(PYTEST + [test], cwd=PROJEKT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=zeit)
    except subprocess.TimeoutExpired:
        return "ZEITLIMIT", []
    return ("OK" if p.returncode == 0 else "FEHLER"), [z for z in p.stdout.splitlines() if z.startswith("E ")][:60]


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("pfade", nargs="+")
    a.add_argument("--zeit", type=int, default=900, help="Sekunden je Test")
    a.add_argument("--grenze-mb", type=float, help="nur neu starten, wenn die Private Bytes darüber liegen")
    a.add_argument("--protokoll", type=Path, help="JSONL-Datei, je Test eine Zeile")
    args = a.parse_args()
    r = lade_rechner()
    tests = [t for p in args.pfade for t in test_ids(p)]
    if not tests:
        print("keine Live-Tests gefunden", flush=True)
        return 1
    try:
        return _laeufe(r, tests, args)
    except NeustartFehler as e:
        print(f"ABBRUCH Neustart: {e}", flush=True)
        return 2


def _laeufe(r, tests: list[str], args) -> int:
    schlecht = 0
    for test in tests:
        vorher = sw_privat_mb()
        neu = None
        if args.grenze_mb is None or vorher is None or vorher > args.grenze_mb:
            neu = neustart(r)
        pids = instanzen()
        beginn = time.time()
        if len(pids) == 1:
            with Spitzenmessung(pids[0]) as speicher:
                ergebnis, fehler = lauf(test, args.zeit)
            mb = speicher.als_dict()
        else:
            ergebnis, fehler = lauf(test, args.zeit)
            mb = None
        dauer = round(time.time() - beginn, 1)
        spitze = f"{mb['spitze']:8.0f} MB" if mb else "       ? MB"
        print(f"{ergebnis:9} {dauer:7.1f} s {spitze}  {test}", flush=True)
        for z in fehler[:10]:
            print("    " + z, flush=True)
        if args.protokoll:
            eintrag = {"test": test, "ergebnis": ergebnis, "dauer_s": dauer, "privat_mb": mb, "neustart": neu,
                       "fehler": fehler}
            with args.protokoll.open("a", encoding="utf-8") as f:
                f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        if ergebnis != "OK":
            schlecht += 1
        if ergebnis == "ZEITLIMIT" and args.grenze_mb is not None:
            neustart(r)   # ohne Grenze startet ohnehin jeder Test frisch
    print(f"nicht OK: {schlecht} von {len(tests)}", flush=True)
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
