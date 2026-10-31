"""Teile ohne Fenster öffnen (BTP Umbau 1): ein sichtbar geöffnetes Normteil kostet SolidWorks ~1,7 GB Private Bytes,
unsichtbar ~1 MB (Spike 24.10.2026). SolidWorks schließt unsichtbare Dokumente mit, sobald ein sichtbares schließt, das
sie hält (Baugruppe) – schliesse() nimmt das hin."""

from pathlib import Path

import pytest

from swki.compiler import sw
from swki.pruefung import messen


class _App:
    def __init__(self, ergebnis=True):
        self.log, self.ergebnis = [], ergebnis

    def DocumentVisible(self, sichtbar, typ):  # noqa: N802 (SolidWorks-Name)
        self.log.append(("sichtbar", sichtbar, typ))

    def OpenDoc6(self, pfad, typ, optionen, konfig, fehler, warnungen):  # noqa: N802 (SolidWorks-Name)
        self.log.append(("oeffne", Path(pfad).name, typ))
        if self.ergebnis is None:
            raise RuntimeError("COM")
        warnungen.value = 0
        return object()

    def CloseDoc(self, titel):  # noqa: N802 (SolidWorks-Name)
        self.log.append(("schliesse", titel))


def test_oeffne_unsichtbar_und_danach_wieder_sichtbar():
    app = _App()
    messen.oeffne(app, Path("a.sldprt"), sichtbar=False)
    assert app.log == [("sichtbar", False, 1), ("oeffne", "a.sldprt", 1), ("sichtbar", True, 1)]


def test_oeffne_unsichtbar_stellt_auch_nach_einem_fehler_zurueck():
    app = _App(ergebnis=None)
    with pytest.raises(RuntimeError):
        messen.oeffne(app, Path("b.sldasm"), sichtbar=False)
    assert app.log[-1] == ("sichtbar", True, 2)


def test_oeffne_sichtbar_wie_bisher():
    app = _App()
    messen.oeffne(app, Path("a.sldprt"))
    assert app.log == [("oeffne", "a.sldprt", 1)]


class _Gleicher(_App):
    def OpenDoc6(self, pfad, typ, optionen, konfig, fehler, warnungen):  # noqa: N802 (SolidWorks-Name)
        fehler.value = 65536  # swFileLoadError_e.swFileWithSameTitleAlreadyOpen
        return None


def test_gleichnamiges_dokument_wird_im_klartext_gemeldet():
    with pytest.raises(messen.PruefFehler, match="gleichnamiges Dokument"):
        messen.oeffne(_Gleicher(), Path("a.sldprt"))


class _Tot:
    @property
    def GetTitle(self):  # noqa: N802 (SolidWorks-Name)
        raise AttributeError("<unknown>.GetTitle")


def test_schliesse_nimmt_ein_schon_mitgeschlossenes_dokument_hin():
    app = _App()
    sw.schliesse(app, _Tot())
    assert app.log == []
