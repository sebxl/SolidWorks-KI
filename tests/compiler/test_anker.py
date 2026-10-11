import pytest

from swki.compiler.anker import (
    AnkerFehler, Flaeche, Kante, flaeche_in_richtung, naechste, punkt_achse_abstand, senkrechte_kanten,
    zylinder_durch_punkt, zylinder_zu_punkten,
)
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN

# Quader 100 x 20 x 60 (x, y, z), Unterseite auf y=0, Tasche mit Boden auf y=10
OBEN = Flaeche("ebene", (0, 20, 0), normale=(0, 1, 0))
TASCHENBODEN = Flaeche("ebene", (0, 10, 0), normale=(0, 1, 0))
UNTEN = Flaeche("ebene", (0, 0, 0), normale=(0, -1, 0))
RECHTS = Flaeche("ebene", (50, 10, 0), normale=(1, 0, 0))
ZYL = Flaeche("zylinder", (30, 0, 0), achse=(0, 1, 0), radius=4)


def test_flaeche_in_richtung_waehlt_aeusserste():
    assert flaeche_in_richtung([UNTEN, TASCHENBODEN, OBEN, ZYL], "+y") is OBEN
    assert flaeche_in_richtung([UNTEN, OBEN], "-y") is UNTEN


def test_flaeche_in_richtung_fehlt():
    with pytest.raises(AnkerFehler) as e:
        flaeche_in_richtung([OBEN, UNTEN], "+z")
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def test_flaeche_in_richtung_mehrdeutig():
    zweite = Flaeche("ebene", (40, 20, 10), normale=(0, 1, 0))
    with pytest.raises(AnkerFehler) as e:
        flaeche_in_richtung([OBEN, zweite], "+y")
    assert e.value.code == REFERENZ_MEHRDEUTIG


def test_flaeche_in_richtung_koplanar_fuer_messung():
    # Zapfen so hoch wie die Stirn teilt sie in zwei Teilflächen derselben Ebene: zum Messen eindeutig, zum Bauen nicht
    teil = Flaeche("ebene", (40, 20, 10), normale=(0, 1, 0))
    assert flaeche_in_richtung([OBEN, teil, TASCHENBODEN], "+y", koplanar_ok=True) is OBEN
    with pytest.raises(AnkerFehler) as e:
        flaeche_in_richtung([OBEN, teil], "+y")
    assert e.value.code == REFERENZ_MEHRDEUTIG


def test_senkrechte_kanten():
    senkrecht = Kante("linie", (50, 0, 30), (50, 20, 30), richtung=(0, 1, 0))
    umgekehrt = Kante("linie", (-50, 20, 30), (-50, 0, 30), richtung=(0, -1, 0))
    waagrecht = Kante("linie", (-50, 20, 30), (50, 20, 30), richtung=(1, 0, 0))
    bogen = Kante("kreis", (0, 0, 0), (0, 0, 0))
    assert senkrechte_kanten([senkrecht, umgekehrt, waagrecht, bogen], (0, 1, 0)) == [senkrecht, umgekehrt]
    with pytest.raises(AnkerFehler):
        senkrechte_kanten([waagrecht], (0, 1, 0))


def test_naechste_eindeutig():
    a = Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.05)
    b = Kante("linie", (0, 0, 0), (0, 1, 0), abstand=3.0)
    assert naechste([b, a], 0.1, "Kante") is a


def test_naechste_nicht_gefunden_nennt_abstand():
    with pytest.raises(AnkerFehler, match="nächster Abstand 0.400 mm") as e:
        naechste([Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.4)], 0.1, "Kante")
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def test_naechste_mehrdeutig():
    kanten = [Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.0), Kante("linie", (0, 0, 0), (0, 1, 0), abstand=0.0)]
    with pytest.raises(AnkerFehler) as e:
        naechste(kanten, 0.1, "Kante")
    assert e.value.code == REFERENZ_MEHRDEUTIG


def test_punkt_achse_abstand():
    assert punkt_achse_abstand((3, 7, 4), (0, 0, 0), (0, 1, 0)) == pytest.approx(5.0)


def test_zylinder_zu_punkten_in_positionsreihenfolge():
    senkung = Flaeche("zylinder", (30, 20, 0), achse=(0, 1, 0), radius=7)
    zweite = Flaeche("zylinder", (-30, 0, 0), achse=(0, -1, 0), radius=4)
    zugeordnet = zylinder_zu_punkten([zweite, senkung, ZYL], [(30, 20, 0), (-30, 20, 0)], 0.01)
    assert zugeordnet == [ZYL, zweite]


def test_zylinder_fehlt():
    with pytest.raises(AnkerFehler, match="Instanz 2"):
        zylinder_zu_punkten([ZYL], [(30, 20, 0), (0, 20, 0)], 0.01)


def _zyl(r, x=0.0):
    return Flaeche("zylinder", (x, 0.0, 0.0), achse=(0.0, 1.0, 0.0), radius=r)


def test_zylinder_durch_punkt():
    assert zylinder_durch_punkt([_zyl(4), _zyl(6.5)], (6.5, 10, 0), 0.1).radius == 6.5


def test_zylinder_durch_punkt_geteilte_flaeche():
    assert zylinder_durch_punkt([_zyl(4), _zyl(4)], (0, 3, 4), 0.1).radius == 4


def test_zylinder_durch_punkt_fehlt():
    with pytest.raises(AnkerFehler) as e:
        zylinder_durch_punkt([_zyl(4)], (5, 0, 0), 0.1)
    assert e.value.daten["code"] == REFERENZ_NICHT_GEFUNDEN


def test_zylinder_durch_punkt_mehrdeutig():
    with pytest.raises(AnkerFehler) as e:
        zylinder_durch_punkt([_zyl(4), _zyl(5, x=9)], (4, 0, 0), 0.1)
    assert e.value.daten["code"] == REFERENZ_MEHRDEUTIG
