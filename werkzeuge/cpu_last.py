"""CPU-Last erzeugen: n Prozesse rechnen bis zur Dauer (Sekunden). Zu werkzeuge.bau_wiederholen (Zeitrennen unter Last).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.cpu_last <n> <dauer_s>
"""

import multiprocessing as mp
import sys
import time


def brenne(ende: float) -> None:
    x = 0
    while time.time() < ende:
        x = (x * 31 + 7) % 1000003


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    n, dauer = int(sys.argv[1]), float(sys.argv[2])
    ende = time.time() + dauer
    ps = [mp.Process(target=brenne, args=(ende,)) for _ in range(n)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
