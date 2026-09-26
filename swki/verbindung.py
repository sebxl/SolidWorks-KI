"""Anbindung an ein laufendes SolidWorks und Hilfen für pywin32."""

import math

from swki.cli import SwkiFehler

_REVISION_BASIS = 1992  # Revision 33 = SOLIDWORKS 2025, 34 = 2026


class SolidWorksNichtGestartet(SwkiFehler):
    pass


class FalscheVersion(SwkiFehler):
    pass


def jahr_aus_revision(revision: str) -> int:
    return int(str(revision).split(".")[0]) + _REVISION_BASIS


def mm(x: float) -> float:
    return x / 1000.0


def in_mm(x: float) -> float:
    return x * 1000.0


def in_mm3(x: float) -> float:
    return round(x * 1e9, 6)


def grad(x: float) -> float:
    return math.radians(x)


def wert(x):
    return x() if callable(x) else x


def callout_leer():
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def byref_long(start: int = 0):
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, start)


def verbinde(jahr: int):
    """Hängt sich an ein laufendes SolidWorks. Startet SolidWorks nicht selbst."""
    import pythoncom
    import win32com.client

    major = jahr - _REVISION_BASIS
    app = None
    for progid in (f"SldWorks.Application.{major}", "SldWorks.Application"):
        try:
            app = win32com.client.GetActiveObject(progid)
            break
        except pythoncom.com_error:
            continue
    if app is None:
        raise SolidWorksNichtGestartet(f"SOLIDWORKS {jahr} läuft nicht. Bitte zuerst starten.")
    ist = jahr_aus_revision(wert(app.RevisionNumber))
    if ist != jahr:
        raise FalscheVersion(f"Laufendes SOLIDWORKS ist {ist}, erwartet {jahr} (config/rechner.yaml).")
    return app
