import pytest

from swki.compiler.anker import Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.skizze import _seite_roh, ebene_aus_flaeche, modellpunkt, orientierung_der_normale
from swki.spec.ausdruck import auswerten


@pytest.mark.parametrize(
    ("orientierung", "erwartet"),
    [("vorne", (30, 10, 5)), ("oben", (30, 5, -10)), ("rechts", (5, 10, -30))],
)
def test_modellpunkt_wie_in_s9a(orientierung, erwartet):
    # S9a Baustein 1: vorne X=u,Y=v · oben X=u,Z=-v · rechts Z=-u,Y=v; Lage 5 auf der Normalenachse
    assert modellpunkt(orientierung, 30, 10, 5) == erwartet


@pytest.mark.parametrize(
    ("normale", "orientierung"),
    [((0, 1, 0), "oben"), ((0, -1, 0), "oben"), ((1, 0, 0), "rechts"), ((0, 0, -1), "vorne")],
)
def test_orientierung_der_normale(normale, orientierung):
    assert orientierung_der_normale(normale) == orientierung


def test_schraege_flaeche_wird_abgelehnt():
    with pytest.raises(BauFehler, match="nicht achsparallel"):
        orientierung_der_normale((0.0, 0.7071, 0.7071))


def test_ebene_aus_deckflaeche():
    se = ebene_aus_flaeche(Flaeche("ebene", (12, 46, -3), normale=(0, 1, 0)))
    assert (se.orientierung, se.lage, se.normale) == ("oben", 46, (0, 1, 0))
    assert se.flaeche.punkt == (12, 46, -3)  # Skizzenfläche für Rand- und Flächenbezüge


def test_zylinder_ist_keine_skizzenebene():
    with pytest.raises(BauFehler, match="ebenen Flächen"):
        ebene_aus_flaeche(Flaeche("zylinder", (0, 0, 0), achse=(0, 1, 0), radius=4))


@pytest.mark.parametrize(("mitte", "groesse", "richtung", "erwartet"), [
    (0, 100, -1, -50), (10, 20.5, 1, 20.25), ("=M", 100, -1, "=(M) - 100 / 2"), (0, "=L", 1, "=0 + (L) / 2"),
    ("=M+1", "=L", -1, "=(M+1) - (L) / 2")])
def test_seite_roh(mitte, groesse, richtung, erwartet):
    # Rechteckseite als Zahl oder Ausdruck – mit Gleichungen hängt sie an den Parametern (Ruling 7)
    ergebnis = _seite_roh(mitte, groesse, richtung)
    assert ergebnis == erwartet
    soll = auswerten(mitte, {"M": 3}) + richtung * auswerten(groesse, {"L": 10}) / 2
    assert auswerten(ergebnis, {"M": 3, "L": 10}) == soll
