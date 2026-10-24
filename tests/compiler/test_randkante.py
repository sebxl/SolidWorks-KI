import pytest

from swki.compiler.anker import AnkerFehler, Kante, randkante
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN

X = (1.0, 0.0, 0.0)
TOL = 1e-3


def linie(start, ende):
    d = tuple(e - s for s, e in zip(start, ende))
    n = sum(c * c for c in d) ** 0.5
    return Kante("linie", start, ende, richtung=tuple(c / n for c in d))


# Deckfläche 100 x 60 in der xz-Ebene (y = 20)
LINKS = linie((-50, 20, -30), (-50, 20, 30))
RECHTS = linie((50, 20, -30), (50, 20, 30))
VORNE = linie((-50, 20, 30), (50, 20, 30))
HINTEN = linie((-50, 20, -30), (50, 20, -30))
DECKEL = [LINKS, RECHTS, VORNE, HINTEN]


def test_aeusserste_kante_in_minus_richtung():
    assert randkante(DECKEL, X, -1, (-30, 20, 0), TOL) is LINKS


def test_aeusserste_kante_in_plus_richtung():
    assert randkante(DECKEL, X, +1, (-30, 20, 0), TOL) is RECHTS


def test_aeusserste_kante_in_z_richtung():
    assert randkante(DECKEL, (0.0, 0.0, 1.0), +1, (0, 20, 0), TOL) is VORNE
    assert randkante(DECKEL, (0.0, 0.0, 1.0), -1, (0, 20, 0), TOL) is HINTEN


def test_unterbrochener_rand_waehlt_die_naechste():
    oben = linie((-50, 20, -30), (-50, 20, -5))
    unten = linie((-50, 20, 5), (-50, 20, 30))
    kanten = [oben, unten, RECHTS, VORNE, HINTEN]
    assert randkante(kanten, X, -1, (-30, 20, -20), TOL) is oben
    assert randkante(kanten, X, -1, (-30, 20, 12), TOL) is unten


def test_gleichstand_ist_mehrdeutig():
    oben = linie((-50, 20, -30), (-50, 20, -5))
    unten = linie((-50, 20, 5), (-50, 20, 30))
    with pytest.raises(AnkerFehler) as e:
        randkante([oben, unten, RECHTS], X, -1, (-30, 20, 0), TOL)
    assert e.value.code == REFERENZ_MEHRDEUTIG
    assert "mehrdeutig" in str(e.value)


def test_innere_kante_zaehlt_nicht():
    # Tasche im Deckel: ihre Wand bei x = -20 liegt weiter innen als der Rand bei x = -50
    wand = linie((-20, 20, -10), (-20, 20, 10))
    assert randkante([wand, LINKS, RECHTS], X, -1, (0, 20, 0), TOL) is LINKS


def test_keine_parallele_kante():
    nur_quer = [VORNE, HINTEN]
    with pytest.raises(AnkerFehler) as e:
        randkante(nur_quer, X, -1, (0, 20, 0), TOL)
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def test_kreise_und_leere_liste():
    kreis = Kante("kreis", (0, 0, 0), (0, 0, 0))
    for kanten in ([kreis], []):
        with pytest.raises(AnkerFehler) as e:
            randkante(kanten, X, -1, (0, 0, 0), TOL)
        assert e.value.code == REFERENZ_NICHT_GEFUNDEN
