from pathlib import Path

import pytest

from swki.api.typbib import lese_typbibliothek

STDOLE = Path(r"C:\Windows\System32\stdole2.tlb")
pytestmark = pytest.mark.skipif(not STDOLE.exists(), reason="stdole2.tlb fehlt")


@pytest.fixture(scope="module")
def stdole():
    return lese_typbibliothek(STDOLE)


def test_enum_werte(stdole):
    _, enums = stdole
    werte = {(e.enum, e.name): e.wert for e in enums}
    assert werte[("OLE_TRISTATE", "Unchecked")] == 0
    assert werte[("OLE_TRISTATE", "Checked")] == 1
    assert werte[("OLE_TRISTATE", "Gray")] == 2


def test_dispatch_methode_mit_parameter(stdole):
    members, _ = stdole
    m = next(m for m in members if m.interface == "FontEvents" and m.name == "FontChanged")
    assert m.art == "methode"
    assert [p.name for p in m.parameter] == ["PropertyName"]


def test_dispinterface_property(stdole):
    members, _ = stdole
    assert any(m.interface == "Font" and m.name == "Name" for m in members)


def test_idispatch_methoden_ausgefiltert(stdole):
    members, _ = stdole
    assert not any(m.name in ("QueryInterface", "Invoke") for m in members)
