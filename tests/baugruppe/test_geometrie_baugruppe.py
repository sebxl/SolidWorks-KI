import math

import pytest

from swki.baugruppe.geometrie import einschraublaenge, transformiere, ueberlappung_soll
from swki.pruefung.geometrie import Messgeometrie

IDENT = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _numerisch(d, p, kernloch, laenge, schritte=200000):
    """Mittelpunktsumme über den Schaft hinter dem Eintritt; s = Abstand von der Spitze."""
    rn, rk, h = d / 2, kernloch / 2, laenge / schritte
    summe = 0.0
    for k in range(schritte):
        s = (k + 0.5) * h
        r = rn - p + s if s < p else rn
        summe += math.pi * max(r * r - rk * rk, 0.0) * h
    return summe


def test_transform_identitaet():
    g = transformiere(Messgeometrie("ebene", (1.0, 2.0, 3.0), (0.0, 1.0, 0.0)), IDENT)
    assert (g.art, g.punkt, g.richtung) == ("ebene", (1.0, 2.0, 3.0), (0.0, 1.0, 0.0))


def test_transform_verschiebung():
    t = IDENT[:9] + [0.01, 0.02, 0.03] + IDENT[12:]
    g = transformiere(Messgeometrie("achse", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), t)
    assert g.punkt == pytest.approx((11.0, 20.0, 30.0)) and g.richtung == (0.0, 0.0, 1.0)


def test_transform_drehung_um_y():
    # +90° um Y: Bild der x-Achse = (0, 0, −1), Bild der z-Achse = (1, 0, 0) (Zeilen 0 und 2)
    t = [0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    g = transformiere(Messgeometrie("achse", (1.0, 0.0, 0.0), (0.0, 0.0, 2.0)), t)
    assert g.punkt == pytest.approx((0.0, 0.0, -1.0)) and g.richtung == pytest.approx((1.0, 0.0, 0.0))


def test_einschraublaenge():
    kopf = Messgeometrie("ebene", (-30.0, 26.4, 0.0), (0.0, 1.0, 0.0))
    assert einschraublaenge(16.0, kopf, Messgeometrie("punkt", (-30.0, 20.0, 0.0))) == pytest.approx(9.6)


def test_ueberlappung_gegen_numerik():
    assert ueberlappung_soll(8, 1.25, 6.8, 13.6) == pytest.approx(_numerisch(8, 1.25, 6.8, 13.6), rel=1e-6)


def test_ueberlappung_nur_fase():
    assert ueberlappung_soll(8, 1.25, 6.8, 0.9) == pytest.approx(_numerisch(8, 1.25, 6.8, 0.9), rel=1e-6)


def test_ueberlappung_ohne_eingriff():
    assert ueberlappung_soll(8, 1.25, 6.8, 0.0) == 0.0 and ueberlappung_soll(8, 1.25, 6.8, -2.0) == 0.0
