"""werkzeuge.sw_neustart ohne SolidWorks: Start im Hintergrund (Nutzer 07.11.2026: SolidWorks drängt sich sonst bei jedem Neustart
und jeder Änderung in den Vordergrund)."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import werkzeuge.sw_neustart as wn


class App:
    StartupProcessCompleted, Visible = True, True

    def __init__(self):
        self.FrameState = 0


def _starte(monkeypatch, hintergrund):
    aufrufe, app = [], App()
    monkeypatch.setattr(wn.subprocess, "Popen", lambda args, **k: aufrufe.append(k))
    monkeypatch.setattr(wn, "verbinde", lambda jahr: app)
    monkeypatch.setattr(wn.time, "sleep", lambda s: None)
    monkeypatch.setattr(wn, "lade_standard", lambda: {"solidworks_hintergrund": hintergrund})
    r = SimpleNamespace(installationsordner=Path("C:/SW"), sw_jahr=2025)
    assert wn.starten(r)[0] is app
    return aufrufe[0], app


def test_start_im_hintergrund_minimiert_ohne_fokus(monkeypatch):
    k, app = _starte(monkeypatch, True)
    info = k["startupinfo"]
    assert info.dwFlags & subprocess.STARTF_USESHOWWINDOW and info.wShowWindow == wn.SW_SHOWMINNOACTIVE
    assert app.FrameState == wn.SW_FENSTER_MINIMIERT == 2   # swWindowState_e.swWindowMinimized (live: bleibt beim Öffnen und
                                                            # bei Screenshots minimiert, Bilder werden gerendert)


def test_start_im_vordergrund_wenn_abgeschaltet(monkeypatch):
    k, app = _starte(monkeypatch, False)
    assert "startupinfo" not in k and app.FrameState == 0
