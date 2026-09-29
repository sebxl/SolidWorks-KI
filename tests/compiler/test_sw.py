import pytest

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
