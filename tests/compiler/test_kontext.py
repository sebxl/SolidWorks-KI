from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import Kontext


class _Gleichungen:
    def __init__(self, rueckgabe: int = 0):
        self.texte, self.rueckgabe = [], rueckgabe

    def Add2(self, index, text, loesen):
        self.texte.append(text)
        return self.rueckgabe


def _ctx(rueckgabe: int = 0) -> Kontext:
    model = SimpleNamespace(GetEquationMgr=_Gleichungen(rueckgabe))
    return Kontext(None, model, {"parameter": {"L": 100}}, Path("x.yaml"), 0.1)


def test_feste_zahl_wird_nicht_gebunden():
    ctx = _ctx()
    ctx.verknuepfe("D1@f1", 20)
    assert ctx.model.GetEquationMgr.texte == []


def test_ausdruck_wird_als_gleichung_gebunden():
    ctx = _ctx()
    ctx.verknuepfe("D1@f1", "=L")
    assert ctx.model.GetEquationMgr.texte == ['"D1@f1" = "L"']


def test_vorzeichen_negiert_den_ausdruck():
    ctx = _ctx()
    ctx.verknuepfe("D2@f1_skizze", "=L/2-20", -1)
    assert ctx.model.GetEquationMgr.texte == ['"D2@f1_skizze" = -(("L" / 2) - 20)']


def test_abgelehnte_gleichung_ist_baufehler():
    with pytest.raises(BauFehler) as e:
        _ctx(rueckgabe=-1).verknuepfe("D1@f1", "=L")
    assert "D1@f1" in str(e.value)
