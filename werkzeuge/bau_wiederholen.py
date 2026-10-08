"""Sporadische Baufehler reproduzieren: Zyklen „SolidWorks neu starten + N × swki bauen <spec>“ bis zum ersten Fehlbau.

Herkunft: Diagnose des sporadischen Normbohrungsfehlers (auftraege/REPRO-NB/diagnose/STAND.md, Fix PR #11).
Optional CPU-Last parallel: .venv\\Scripts\\python.exe -m werkzeuge.cpu_last <n> <dauer_s> (Last verlangsamt einen Bau
stark – vorher den Nutzer fragen).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.bau_wiederholen <spec> [--zyklen 10] [--bauten 2] [--weiter]
"""

import argparse
import json
import subprocess
import sys
import time

from swki.konfig import PROJEKT, lade_rechner
from werkzeuge.sw_neustart import neustart


def bauen(spec: str) -> dict:
    p = subprocess.run([sys.executable, "-m", "swki", "bauen", spec], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=PROJEKT, timeout=900)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"roh": p.stdout[-2000:], "err": p.stderr[-2000:]}


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("spec")
    a.add_argument("--zyklen", type=int, default=10)
    a.add_argument("--bauten", type=int, default=2, help="Bauten je frischem SolidWorks")
    a.add_argument("--weiter", action="store_true", help="nach einem Fehlbau nicht anhalten")
    args = a.parse_args()
    r = lade_rechner()
    fehl = 0
    for z in range(1, args.zyklen + 1):
        neustart(r)
        for b in range(1, args.bauten + 1):
            t = time.time()
            erg = bauen(args.spec)
            status = erg.get("status") or (erg.get("fehler") or {}).get("code") or "?"
            text = json.dumps(erg.get("fehler"), ensure_ascii=False)[:400] if erg.get("status") != "ok" else ""
            print(f"Zyklus {z} Bau {b}: {status} lauf={erg.get('lauf')} {time.time() - t:.0f}s {text}", flush=True)
            if erg.get("status") != "ok":
                fehl += 1
                if "roh" in erg:
                    print(erg, flush=True)
                if not args.weiter:
                    return 1
    print(f"Fehlbauten: {fehl}", flush=True)
    return 1 if fehl else 0


if __name__ == "__main__":
    sys.exit(main())
