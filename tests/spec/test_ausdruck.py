import math

import pytest

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck, namen, sw_ausdruck


def test_zahl_bleibt_zahl():
    assert auswerten(296) == 296.0
    assert auswerten(2.5) == 2.5


def test_ausdruck_mit_parametern():
    assert auswerten("=L/2-20", {"L": 296}) == 128.0
    assert auswerten("=-(B+4)*2", {"B": 1}) == -10.0
    assert auswerten("=2**3") == 8.0


def test_ist_ausdruck():
    assert ist_ausdruck("=L")
    assert not ist_ausdruck("L")
    assert not ist_ausdruck(5)


def test_unbekannter_parameter_nennt_namen():
    with pytest.raises(AusdruckFehler, match="'X'"):
        auswerten("=X*2", {"L": 1})


@pytest.mark.parametrize("text", ["=__import__('os')", "=L.real", "=1 if L else 2", "=True", "=[1]", "=L(2)"])
def test_verbotene_konstrukte(text):
    with pytest.raises(AusdruckFehler):
        auswerten(text, {"L": 1})


def test_syntaxfehler():
    with pytest.raises(AusdruckFehler, match="ungültig"):
        auswerten("=L*/2", {"L": 1})


def test_division_durch_null():
    with pytest.raises(AusdruckFehler, match="Division durch 0"):
        auswerten("=L/(B-B)", {"L": 1, "B": 2})


def test_bool_und_text_sind_keine_werte():
    with pytest.raises(AusdruckFehler):
        auswerten(True)
    with pytest.raises(AusdruckFehler):
        auswerten("L")


def test_namen():
    assert namen("=L/2-B") == {"L", "B"}
    assert namen("=5") == set()


def test_sw_ausdruck():
    assert sw_ausdruck("=L/2-20") == '("L" / 2) - 20'
    assert sw_ausdruck("=L") == '"L"'
    assert sw_ausdruck("=-L*2**2") == '-"L" * (2 ^ 2)'


def test_konstante_pi():
    assert auswerten("=pi*M", {"M": 2}) == pytest.approx(2 * math.pi)
    assert sw_ausdruck("=HUB*360/(pi*40)") == '("HUB" * 360) / (pi * 40)'
    assert namen("=pi*M/Z") == {"M", "Z"}
