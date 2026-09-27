"""Live-Tests einzeln mit Zeitlimit ausführen (ein hängendes SolidWorks blockiert sonst die ganze Suite).

Aufruf:  .venv\\Scripts\\python.exe tests\\live_einzeln.py tests\\live\\test_live_extrusion.py [weitere …] [--zeit 120]
Jeder Test läuft in einem eigenen pytest-Prozess. Beim ersten Zeitüberschreiten wird abgebrochen (Exit 2) –
dann SolidWorks prüfen (reagiert es?) und die Benutzereinstellung swInputDimValOnCreate kontrollieren,
weil ein hart beendeter Prozess sie nicht mehr zurücksetzen konnte.
"""

import argparse
import subprocess
import sys


def tests_in(pfad: str) -> list[str]:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "sw", pfad, "--collect-only", "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return [z.strip() for z in ergebnis.stdout.splitlines() if "::" in z]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pfade", nargs="+")
    parser.add_argument("--zeit", type=int, default=120, help="Sekunden je Test")
    args = parser.parse_args()
    fehler = 0
    for pfad in args.pfade:
        for test in tests_in(pfad):
            try:
                lauf = subprocess.run(
                    [sys.executable, "-m", "pytest", "-m", "sw", test, "-q", "-p", "no:cacheprovider"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.zeit,
                )
            except subprocess.TimeoutExpired:
                print(f"ZEITLIMIT {test} – SolidWorks prüfen, Einstellungen kontrollieren", flush=True)
                return 2
            if lauf.returncode == 0:
                print(f"OK      {test}", flush=True)
            else:
                fehler += 1
                print(f"FEHLER  {test}", flush=True)
                print("\n".join(z for z in lauf.stdout.splitlines() if z.startswith("E ")), flush=True)
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
