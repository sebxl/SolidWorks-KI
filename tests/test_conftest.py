"""Die Fixture `auftrag` löscht im echten Arbeitsordner: nur Testaufträge."""

import pytest

from tests.conftest import nur_testauftrag


@pytest.mark.parametrize("name", ["LIVE-BESTAND", "REF-BESTAND"])
def test_testauftraege_gehen(name):
    assert nur_testauftrag(name) == name


@pytest.mark.parametrize("name", ["MKA25-Lagerdeckel", "SWKI-LIVE-BESTAND", "", "live-bestand", "LIVE"])
def test_andere_auftraege_werden_nie_geloescht(name):
    with pytest.raises(ValueError, match="Testauftrag"):
        nur_testauftrag(name)
