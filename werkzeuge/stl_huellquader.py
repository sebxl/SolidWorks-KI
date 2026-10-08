"""Hüllquader aller STL eines Ordners (binär oder ASCII), sortiert nach Dateiname; ohne SolidWorks und Blender.

Herkunft: AP 6.8, Maschinen-Hüllquader aus dem Blender-STL-Export (UEBERGABE §10.3).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.stl_huellquader <ordner> [--bereich X0 X1 Y0 Y1 Z0 Z1]
--bereich zeigt nur Teile, deren Hüllquader den Bereich berührt (Einheit wie in den STL, beim Export mm).
"""

import argparse
import struct
import sys
from pathlib import Path


def huellquader(pfad: Path) -> tuple[list[float], list[float]]:
    """(min [x, y, z], max [x, y, z]) aller Eckpunkte. Binär, wenn die Dateigröße 84 + 50·n passt, sonst ASCII."""
    d = Path(pfad).read_bytes()
    n = struct.unpack_from("<I", d, 80)[0] if len(d) >= 84 else -1
    punkte = []
    if len(d) == 84 + 50 * n:
        for i in range(n):
            o = 84 + 50 * i + 12
            punkte += [struct.unpack_from("<3f", d, o + 12 * k) for k in range(3)]
    else:
        for zeile in d.decode("ascii", "ignore").splitlines():
            t = zeile.split()
            if t and t[0] == "vertex":
                punkte.append(tuple(map(float, t[1:4])))
    if not punkte:
        raise ValueError(f"{pfad}: keine Eckpunkte")
    return [min(p[j] for p in punkte) for j in range(3)], [max(p[j] for p in punkte) for j in range(3)]


def beruehrt(lo, hi, bereich) -> bool:
    return all(lo[j] <= bereich[2 * j + 1] and hi[j] >= bereich[2 * j] for j in range(3))


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("ordner", type=Path)
    a.add_argument("--bereich", type=float, nargs=6, metavar=("X0", "X1", "Y0", "Y1", "Z0", "Z1"))
    args = a.parse_args()
    for p in sorted(args.ordner.glob("*.stl")):
        lo, hi = huellquader(p)
        if args.bereich and not beruehrt(lo, hi, args.bereich):
            continue
        print(f"{p.stem:28s} X {lo[0]:8.1f} … {hi[0]:8.1f}  Y {lo[1]:7.1f} … {hi[1]:7.1f}  Z {lo[2]:7.1f} … {hi[2]:7.1f}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
