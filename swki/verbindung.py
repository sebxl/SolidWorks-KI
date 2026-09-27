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
    """Nur für Getter/Properties mit primitivem Rückgabewert (str, int, bool, …) geeignet:
    ist x nicht callable, wird x unverändert zurückgegeben; ist x callable, wird x() aufgerufen.

    Einschränkung (gefunden in Stufe 0, Spike S2/S3/S4, siehe docs/stufe0/ergebnisse): bei
    nullargumentigen Membern, die ein COM-Objekt liefern (z. B. IModelDoc2.FirstFeature,
    IFeature.GetNextFeature, IModelDocExtension.CreateMassProperty), ruft pywin32s dynamischer
    Dispatch den Member schon beim Attributzugriff auf – x ist dann bereits das Ergebnis, kein
    Methoden-Stub. Da jedes win32com.client.CDispatch-Objekt selbst __call__ definiert, ist auch
    dieses Ergebnis "callable", und wert() würde es fälschlich nochmal aufrufen
    (com_error 'Mitglied nicht gefunden'). Für solche Member reinen Attributzugriff ohne wert()
    verwenden, z. B. `model.FirstFeature` statt `wert(model.FirstFeature)`.
    """
    return x() if callable(x) else x


def callout_leer():
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def byref_long(start: int = 0):
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, start)


def byref_bool():
    """ByRef-bool-Ausgabeparameter (z. B. IFeature.GetErrorCode2); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BOOL, False)


def byref_variant():
    """ByRef-Ausgabeparameter für Arrays/Objekte (z. B. GetWhatsWrong); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, None)


def byref_str():
    """ByRef-String-Ausgabeparameter (z. B. GetMaterialPropertyName2, Get6); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")


def r8_array(werte) -> object:
    """double-Array für COM. Eine rohe Python-Liste liefert bei IMathUtility.CreatePoint still falsche Werte."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(x) for x in werte])


def verbinde(jahr: int):
    """Hängt sich an ein laufendes SolidWorks (startet es nicht) und liefert es immer late-bound.

    win32com.client.GetActiveObject würde bei vorhandenem gen_py-Cache ein early-bound Objekt liefern,
    für das andere Aufrufregeln gelten (Spike S8/S9a). Der Weg über pythoncom + dynamic.Dispatch
    bleibt in jedem Fall dynamisch.
    """
    import pythoncom
    import win32com.client.dynamic

    major = jahr - _REVISION_BASIS
    unbekannt = None
    for progid in (f"SldWorks.Application.{major}", "SldWorks.Application"):
        try:
            unbekannt = pythoncom.GetActiveObject(progid)
            break
        except pythoncom.com_error:
            continue
    if unbekannt is None:
        raise SolidWorksNichtGestartet(f"SOLIDWORKS {jahr} läuft nicht. Bitte zuerst starten.")
    app = win32com.client.dynamic.Dispatch(unbekannt.QueryInterface(pythoncom.IID_IDispatch))
    ist = jahr_aus_revision(wert(app.RevisionNumber))
    if ist != jahr:
        raise FalscheVersion(f"Laufendes SOLIDWORKS ist {ist}, erwartet {jahr} (config/rechner.yaml).")
    return app
