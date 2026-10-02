import pytest

from swki.spec.konturen import bogenende_koordinate, eckradien, eckradien_roh, kontur_punkte, kontur_punkte_roh

DREIECK = [[0, 0], [10, 0], [0, 10]]


def test_eckradien_ein_wert_fuer_alle():
    assert eckradien({"punkte": DREIECK, "radien": "=R"}, {"R": 2}) == [2.0, 2.0, 2.0]


def test_eckradien_je_ecke():
    assert eckradien({"punkte": DREIECK, "radien": [0, 1, "=R"]}, {"R": 2}) == [0.0, 1.0, 2.0]


def test_eckradien_ohne_angabe_scharf():
    assert eckradien({"punkte": DREIECK}, {}) == [0.0, 0.0, 0.0]


def test_kontur_punkte():
    kontur = {"start": [0, 0], "segmente": [{"linie": ["=A", 0]}, {"bogen": ["=A", 30], "mitte": ["=A", 15]},
                                            {"linie": [0, 30]}, {"linie": [0, 0]}]}
    assert kontur_punkte_roh(kontur) == [[0, 0], ["=A", 0], ["=A", 30], [0, 30], [0, 0]]
    assert kontur_punkte(kontur, {"A": 40}) == [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0), (0.0, 0.0)]


@pytest.mark.parametrize(("ende", "mitte", "index"), [
    ((40, 30), (40, 15), 0),   # Ende senkrecht über dem Mittelpunkt: u festlegen, v folgt aus dem Radius
    ((55, 15), (40, 15), 1),   # Ende rechts vom Mittelpunkt: v festlegen
    ((50, 25), (40, 15), 0),   # 45°: gleich weit – u
])
def test_bogenende_koordinate(ende, mitte, index):
    assert bogenende_koordinate(ende, mitte) == index


def test_eckradien_roh():
    assert eckradien_roh({"punkte": DREIECK, "radien": "=R"}) == ["=R", "=R", "=R"]
    assert eckradien_roh({"punkte": DREIECK, "radien": [0, 1, "=R"]}) == [0, 1, "=R"]
    assert eckradien_roh({"punkte": DREIECK}) == [0, 0, 0]
