import pytest

from swki.konfig import lade_rechner
from swki.verbindung import jahr_aus_revision, verbinde, wert

pytestmark = pytest.mark.sw


def test_verbinde_mit_laufendem_solidworks():
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    assert jahr_aus_revision(wert(app.RevisionNumber)) == r.sw_jahr
