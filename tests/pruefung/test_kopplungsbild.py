"""kopplungsbild (Spec 4b §5.7): übrige Komponenten während der Aufnahme ausblenden, Zoom auf die Auswahl oder Fallback."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.pruefung import bilder
from swki.pruefung.bilder import kopplungsbild


class _App:
    def __init__(self):
        self.werte = {6: 1}

    def GetUserPreferenceIntegerValue(self, wert_id):
        return self.werte[wert_id]

    def SetUserPreferenceIntegerValue(self, wert_id, wert):
        self.werte[wert_id] = wert


class _Komp:
    def __init__(self, name, sichtbar=1, waehlbar=True, protokoll=None):
        self.name, self.Visible, self.waehlbar, self.protokoll = name, sichtbar, waehlbar, protokoll

    def Select4(self, anhaengen, daten, popup):
        return self.waehlbar


class _Modell:
    def __init__(self, protokoll, uebrige):
        self.protokoll, self.uebrige = protokoll, uebrige
        self.SelectionManager = SimpleNamespace(CreateSelectData=object())

    def _FlagAsMethod(self, name):
        pass

    def ClearSelection2(self, alle):
        pass

    def ShowNamedView2(self, name, ansicht):
        self.protokoll.append(("ansicht", ansicht))

    def _zoom(self, art):
        self.protokoll.append((art, [k.Visible for k in self.uebrige]))

    def ViewZoomToSelection(self):
        self._zoom("auswahl")

    def ViewZoomtofit2(self):
        self._zoom("alles")


@pytest.fixture
def aufnahme(monkeypatch):
    gespeichert = []
    monkeypatch.setattr(bilder.sw, "speichere", lambda model, pfad, kopie=False: model._zoom("speichern") or gespeichert.append(pfad))
    return gespeichert


def _lauf(waehlbar=True, vorher=(1, 0)):
    protokoll = []
    uebrige = [_Komp("bock", vorher[0]), _Komp("platte", vorher[1])]
    gekoppelt = [_Komp("a", waehlbar=waehlbar), _Komp("b")]
    model = _Modell(protokoll, uebrige)
    pfad = Path("k1-eingriff.png")
    assert kopplungsbild(_App(), model, pfad, (0.0, 0.0, 1.0), gekoppelt, uebrige) == str(pfad)
    return protokoll, uebrige


def test_uebrige_komponenten_sind_waehrend_der_aufnahme_unsichtbar_und_danach_wieder_wie_vorher(aufnahme):
    protokoll, uebrige = _lauf()
    assert ("auswahl", [0, 0]) in protokoll and ("speichern", [0, 0]) in protokoll
    assert [k.Visible for k in uebrige] == [1, 0]  # was vorher verborgen war, bleibt verborgen
    assert aufnahme == [Path("k1-eingriff.png")]


def test_ansicht_entlang_der_groessten_achskomponente(aufnahme):
    protokoll, _ = _lauf()
    assert protokoll[0] == ("ansicht", bilder.ANSICHTEN["vorne"])


def test_fallback_auf_zoom_alles_wenn_auswahl_misslingt(aufnahme):
    protokoll, uebrige = _lauf(waehlbar=False)
    arten = [p[0] for p in protokoll]
    assert "alles" in arten and "auswahl" not in arten
    assert ("alles", [0, 0]) in protokoll  # erst ausblenden, dann auf alles zoomen


def test_komponenten_werden_auch_bei_fehler_wieder_eingeblendet(aufnahme, monkeypatch):
    def kaputt(model, pfad, kopie=False):
        raise RuntimeError("Speichern kaputt")

    monkeypatch.setattr(bilder.sw, "speichere", kaputt)
    uebrige = [_Komp("bock")]
    with pytest.raises(RuntimeError):
        kopplungsbild(_App(), _Modell([], uebrige), Path("x.png"), (1.0, 0.0, 0.0), [_Komp("a"), _Komp("b")], uebrige)
    assert uebrige[0].Visible == 1
