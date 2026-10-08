"""Speicher-Abtaster: Private Bytes aller SLDWORKS.exe alle `takt_s` Sekunden als JSONL, bis die Stopp-Datei existiert.
Läuft als eigener, entkoppelter Prozess neben dem Konstruktions-Agenten."""

import json
import subprocess
import sys
import time
from pathlib import Path

from swki.speicher import privat_mb
from werkzeuge.sw_neustart import instanzen


def abtasten(datei: Path, stopp: Path, takt_s: float = 0.5, hoechstens_s: float = 4 * 3600) -> None:
    beginn = time.time()
    with open(datei, "a", encoding="utf-8") as f:
        while not stopp.exists() and time.time() - beginn < hoechstens_s:
            t = time.time()
            for pid in instanzen():
                try:
                    f.write(json.dumps({"t": round(t, 2), "pid": pid, "mb": privat_mb(pid)}) + "\n")
                except OSError:
                    pass
            f.flush()
            time.sleep(max(0.0, takt_s - (time.time() - t)))


def starte(datei: Path, stopp: Path) -> int:
    """Startet den Abtaster entkoppelt (überlebt die Shell des Aufrufers) → PID."""
    stopp.unlink(missing_ok=True)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    p = subprocess.Popen([sys.executable, "-m", "werkzeuge.messstand", "abtasten", str(datei), str(stopp)],
                         creationflags=flags, close_fds=True, cwd=str(Path(__file__).resolve().parents[2]))
    return p.pid


def stoppe(stopp: Path, datei: Path, frist_s: float = 10) -> None:
    stopp.write_text("stopp", encoding="utf-8")
    beginn, groesse = time.time(), -1
    while time.time() - beginn < frist_s:   # warten, bis nichts mehr geschrieben wird
        g = datei.stat().st_size if datei.exists() else 0
        if g == groesse:
            return
        groesse = g
        time.sleep(1.5)


def auswerten(datei: Path) -> dict:
    """Spitze (MB), PIDs in Reihenfolge, Neustarts = PID-Wechsel, Abtastungen."""
    spitze, pids, n = 0.0, [], 0
    for z in Path(datei).read_text(encoding="utf-8").splitlines() if Path(datei).exists() else []:
        d = json.loads(z)
        n += 1
        spitze = max(spitze, d["mb"])
        if not pids or pids[-1] != d["pid"]:
            if d["pid"] not in pids:
                pids.append(d["pid"])
    return {"speicher_spitze_mb": round(spitze, 1), "sw_pids": pids, "sw_neustarts": max(0, len(pids) - 1),
            "abtastungen": n}
