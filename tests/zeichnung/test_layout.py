"""Zeichnungsableitung Z1.3 Stufe 1 (Plan 2026-11-17 Task 4): Anordnung nach Projektionsmethode 1 ohne Überlappung."""

from itertools import combinations

from swki.zeichnung.blatt import SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.layout import MASSRAND_MM, Platz, anordnen


def _rechteck(p: Platz, rand: float = MASSRAND_MM):
    (x, y), (b, h) = p.mitte_mm, p.groesse_mm
    return (x - b / 2 - rand, y - h / 2 - rand, x + b / 2 + rand, y + h / 2 + rand)


def _ueberlappt(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _pruefe(format_, plaetze):
    x0, y0, x1, y1 = zeichenfeld(format_)
    schrift = (x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])
    for p in plaetze:
        r = _rechteck(p)
        assert x0 - 1e-6 <= r[0] and r[2] <= x1 + 1e-6 and y0 - 1e-6 <= r[1] and r[3] <= y1 + 1e-6, p
        assert not _ueberlappt(r, schrift), p
    for a, b in combinations(plaetze, 2):
        assert not _ueberlappt(_rechteck(a), _rechteck(b)), (a, b)


def test_projektionsmethode_1():
    format_, massstab, plaetze = anordnen({"haupt": (100, 60), "seite": (60, 60), "drauf": (100, 40)})
    p = {x.rolle: x for x in plaetze}
    assert abs(p["drauf"].mitte_mm[0] - p["haupt"].mitte_mm[0]) < 1e-6 and p["drauf"].mitte_mm[1] < p["haupt"].mitte_mm[1]
    assert abs(p["seite"].mitte_mm[1] - p["haupt"].mitte_mm[1]) < 1e-6 and p["seite"].mitte_mm[0] > p["haupt"].mitte_mm[0]
    _pruefe(format_, plaetze)


def test_groesse_mit_massstab():
    format_, massstab, plaetze = anordnen({"haupt": (300, 100)})
    f = massstab[0] / massstab[1]
    assert plaetze[0].groesse_mm == (300 * f, 100 * f)
    _pruefe(format_, plaetze)


def test_ragt_ins_schriftfeld_naechster_massstab():
    assert anordnen({"haupt": (170, 240)})[:2] == ("A4", (1, 2))


def test_buchse_aehnlich():
    format_, massstab, plaetze = anordnen({"haupt": (60, 50), "seite": (50, 50)})
    _pruefe(format_, plaetze)


def test_kleines_teil_vergroessert():
    format_, massstab, plaetze = anordnen({"haupt": (20, 8), "drauf": (20, 8)})
    assert format_ == "A4" and massstab[0] > massstab[1]
    _pruefe(format_, plaetze)


def test_zusatzansichten_links_und_oben():
    format_, massstab, plaetze = anordnen({"haupt": (80, 50), "drauf": (80, 20), "seite": (20, 50),
                                          "seite_rechts": (20, 50), "unter": (80, 20)})
    p = {x.rolle: x for x in plaetze}
    assert p["seite_rechts"].mitte_mm[0] < p["haupt"].mitte_mm[0]
    assert abs(p["seite_rechts"].mitte_mm[1] - p["haupt"].mitte_mm[1]) < 1e-6
    assert p["unter"].mitte_mm[1] > p["haupt"].mitte_mm[1]
    assert abs(p["unter"].mitte_mm[0] - p["haupt"].mitte_mm[0]) < 1e-6
    _pruefe(format_, plaetze)
