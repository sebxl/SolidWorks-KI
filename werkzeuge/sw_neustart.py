"""SolidWorks beenden und frisch starten (Skill baugruppe §4, CLAUDE.md „Bewegungen“).

Nur wenn genau eine (oder keine) Instanz läuft und keine Dokumente offen sind – fremde Dokumente werden nie
geschlossen. Gestartet wird `SLDWORKS.exe` aus `installationsordner` (config/rechner.yaml). Danach: genau eine
Instanz, sichtbares Fenster, Einstellungen Toggle 10 (swInputDimValOnCreate) / Integer 6 = False / 1.

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.sw_neustart        (Ausgabe JSON, Exit 1 bei Abbruch)
Als Funktion: from werkzeuge.sw_neustart import neustart
"""

import argparse
import json
import subprocess
import sys
import time

from swki.konfig import lade_rechner
from swki.speicher import privat_mb
from swki.verbindung import verbinde

SW_INPUT_DIM_VAL_ON_CREATE = 10  # swUserPreferenceToggle_e (wie swki.compiler.sw)
EINSTELLUNG_INT_6 = 6            # Skill baugruppe §4: nach dem Start 1 erwartet


class NeustartFehler(RuntimeError):
    pass


def instanzen() -> list[int]:
    """PIDs aller laufenden SLDWORKS.exe."""
    aus = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, encoding="oem", errors="replace").stdout
    return [int(z.split('","')[1]) for z in aus.splitlines() if "SLDWORKS" in z.upper()]


def sw_privat_mb() -> float | None:
    """Private Bytes der einzigen SolidWorks-Instanz (MB) oder None."""
    pids = instanzen()
    if len(pids) != 1:
        return None
    try:
        return privat_mb(pids[0])
    except OSError:
        return None


def beenden(r) -> float:
    """Beendet die laufende Instanz (ExitApp); Sekunden bis kein Prozess mehr läuft."""
    app = verbinde(r.sw_jahr)
    n = app.GetDocumentCount
    if n:
        raise NeustartFehler(f"{n} Dokument(e) offen – kein Neustart (fremde Dokumente nie schließen)")
    app._FlagAsMethod("ExitApp")
    app.ExitApp()
    del app
    beginn = time.time()
    while instanzen():
        if time.time() - beginn > 120:
            raise NeustartFehler("SolidWorks beendet sich nicht (120 s)")
        time.sleep(1)
    return round(time.time() - beginn, 1)


def _starte_entkoppelt(exe) -> None:
    """SolidWorks darf das Ende des aufrufenden Prozesses (Python, Shell des Agenten) nicht mitbekommen."""
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen([str(exe)], creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, close_fds=True)
    except OSError:   # Job ohne Breakaway-Erlaubnis
        subprocess.Popen([str(exe)], creationflags=flags, close_fds=True)


def starten(r, frist_s: int = 300) -> tuple:
    """Startet SolidWorks und wartet, bis COM erreichbar und das Fenster sichtbar ist → (app, Sekunden)."""
    _starte_entkoppelt(r.installationsordner / "SLDWORKS.exe")
    beginn = time.time()
    while time.time() - beginn < frist_s:
        time.sleep(2)
        try:
            app = verbinde(r.sw_jahr)
            if app.StartupProcessCompleted and app.Visible:   # Visible meldet direkt nach dem Start kurz False
                time.sleep(3)
                return app, round(time.time() - beginn, 1)
        except Exception:
            continue
    raise NeustartFehler(f"SolidWorks nach {frist_s} s nicht erreichbar")


def neustart(r=None) -> dict:
    r = r or lade_rechner()
    vorher = instanzen()
    if len(vorher) > 1:
        raise NeustartFehler(f"mehr als eine SolidWorks-Instanz ({vorher}) – klären, nicht neu starten")
    erg = {"privat_mb_vorher": sw_privat_mb(), "beendet_s": beenden(r) if vorher else None}
    app, erg["gestartet_s"] = starten(r)
    toggle, wert = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE), app.GetUserPreferenceIntegerValue(EINSTELLUNG_INT_6)
    erg |= {"instanzen": len(instanzen()), "dokumente": app.GetDocumentCount, "privat_mb": sw_privat_mb(),
            "einstellungen": {"toggle_10": bool(toggle), "integer_6": wert},
            "einstellungen_ok": (not toggle) and wert == 1}
    return erg


def main() -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    try:
        erg = {"status": "ok", **neustart()}
    except NeustartFehler as e:
        erg = {"status": "abbruch", "grund": str(e)}
    print(json.dumps(erg, ensure_ascii=False))
    return 0 if erg["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
