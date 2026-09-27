import pytest

from swki.konfig import lade_rechner
from swki.verbindung import jahr_aus_revision, verbinde, wert

pytestmark = pytest.mark.sw


def test_verbinde_mit_laufendem_solidworks():
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    assert jahr_aus_revision(wert(app.RevisionNumber)) == r.sw_jahr


def test_verbindung_ist_late_bound():
    import win32com.client.dynamic

    app = verbinde(lade_rechner().sw_jahr)
    assert type(app) is win32com.client.dynamic.CDispatch
    assert type(app.GetMathUtility) is win32com.client.dynamic.CDispatch  # auch Kindobjekte dynamisch
