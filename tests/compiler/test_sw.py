from types import SimpleNamespace

import pytest

from swki.compiler import sw
from swki.compiler.fehler import BauFehler
from swki.compiler.sw import einstellung_int


class _FakeApp:
    def __init__(self, wert: int):
        self.wert = wert

    def GetUserPreferenceIntegerValue(self, wert_id: int) -> int:
        return self.wert

    def SetUserPreferenceIntegerValue(self, wert_id: int, wert: int) -> None:
        self.wert = wert


def test_einstellung_int_setzt_und_stellt_wieder_her():
    app = _FakeApp(1)
    with einstellung_int(app, 6, 0):
        assert app.wert == 0
    assert app.wert == 1


def test_einstellung_int_stellt_auch_bei_ausnahme_wieder_her():
    app = _FakeApp(1)
    with pytest.raises(ValueError):
        with einstellung_int(app, 6, 0):
            assert app.wert == 0
            raise ValueError("kaputt")
    assert app.wert == 1


class _FakeExtension:
    def __init__(self):
        self.gespeichert = []

    def SaveAs3(self, pfad, version, optionen, a, b, fehler, warnungen):
        self.gespeichert.append(pfad)
        return True


def test_speichere_nur_im_arbeitsordner(monkeypatch, tmp_path):
    monkeypatch.setattr(sw, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=tmp_path / "arbeit"))
    with pytest.raises(BauFehler) as e:
        sw.speichere(None, tmp_path / "kunde" / "teil.sldprt")
    assert "Arbeitsordner" in str(e.value)
    assert not (tmp_path / "kunde").exists()


def test_speichere_im_arbeitsordner(monkeypatch, tmp_path):
    monkeypatch.setattr(sw, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=tmp_path / "arbeit"))
    model = SimpleNamespace(Extension=_FakeExtension())
    ziel = tmp_path / "arbeit" / "A" / "lauf-1" / "teil.sldprt"
    sw.speichere(model, ziel)
    assert model.Extension.gespeichert == [str(ziel)]
