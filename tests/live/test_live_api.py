import pytest

from swki.api.bauen import api_db
from swki.api.index import enum, methode
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw


@pytest.fixture(scope="module")
def db():
    pfad = api_db(lade_rechner().sw_jahr)
    if not pfad.exists():
        pytest.fail("Index fehlt – zuerst: python -m swki api bauen")
    return pfad


def test_feature_extrusion3_hat_23_parameter(db):
    [m] = methode(db, "IFeatureManager.FeatureExtrusion3")
    assert m["anzahl_parameter"] == 23
    assert m["seit"] is not None and m["seit"] <= 2025


def test_end_conditions(db):
    werte = {e["name"]: e["wert"] for e in enum(db, "swEndConditions_e")}
    assert werte["swEndCondBlind"] == 0
    assert werte["swEndCondThroughAll"] == 1
