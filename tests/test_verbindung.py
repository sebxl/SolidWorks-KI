import math

from swki.verbindung import grad, in_mm, in_mm3, jahr_aus_revision, mm, wert


def test_jahr_aus_revision():
    assert jahr_aus_revision("33.2.0") == 2025
    assert jahr_aus_revision("34.0.1") == 2026


def test_einheiten():
    assert mm(1000) == 1.0
    assert in_mm(0.02) == 20.0
    assert in_mm3(1.2e-4) == 120000.0
    assert grad(180) == math.pi


def test_wert():
    assert wert(lambda: 5) == 5
    assert wert(5) == 5
