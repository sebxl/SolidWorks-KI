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


def test_einzelheit_in_der_freien_ecke_vergroessert():
    """Nutzer 18.11.2026: dichte Hauptansicht → Einzelheit. Sie liegt in der freien Ecke rechts unter der Seitenansicht
    und bekommt einen eigenen, größeren Normmaßstab (möglichst doppelt so groß wie das Blatt)."""
    format_, massstab, plaetze = anordnen({"haupt": (200, 120), "seite": (20, 120), "drauf": (200, 20),
                                          "einzelheit": (60, 35)})
    p = {x.rolle: x for x in plaetze}
    f = massstab[0] / massstab[1]
    e = p["einzelheit"]
    assert e.massstab is not None and e.massstab[0] / e.massstab[1] >= 2 * f - 1e-9
    assert e.groesse_mm == (60 * e.massstab[0] / e.massstab[1], 35 * e.massstab[0] / e.massstab[1])
    assert e.mitte_mm[0] > p["haupt"].mitte_mm[0] and e.mitte_mm[1] < p["haupt"].mitte_mm[1]
    assert abs(p["seite"].mitte_mm[1] - p["haupt"].mitte_mm[1]) < 1e-6  # Projektion bleibt ausgerichtet
    _pruefe(format_, plaetze)


def test_einzelheit_aendert_den_blattmassstab_nicht_ohne_not():
    ohne = anordnen({"haupt": (200, 120), "seite": (20, 120), "drauf": (200, 20)})[:2]
    mit = anordnen({"haupt": (200, 120), "seite": (20, 120), "drauf": (200, 20), "einzelheit": (60, 35)})[:2]
    assert mit == ohne


def test_einzelheit_rechts_neben_der_seitenansicht_wenn_die_ecke_zu_klein_ist():
    """Vergrößern geht vor der Ecke: passt die vergrößerte Einzelheit nicht unter die Seitenansicht, dann rechts daneben."""
    format_, massstab, plaetze = anordnen({"haupt": (224, 144), "seite": (44, 144), "drauf": (224, 44),
                                          "einzelheit": (100, 60)})
    p = {x.rolle: x for x in plaetze}
    assert (format_, massstab) == ("A3quer", (1, 2)) and p["einzelheit"].massstab == (1, 1)
    assert p["einzelheit"].mitte_mm[0] > p["seite"].mitte_mm[0]
    assert abs(p["einzelheit"].mitte_mm[1] - p["haupt"].mitte_mm[1]) < 1e-6
    _pruefe(format_, plaetze)


def test_einzelheit_passt_nur_vergroessert_und_ohne_kleineren_blattmassstab():
    """Nutzer 18.11.2026: „Details werden in der Regel vergrößert, sonst braucht man kein Detail.“"""
    from swki.zeichnung.layout import einzelheit_passt

    ansichten = {"haupt": (224, 144), "seite": (44, 144), "drauf": (224, 44)}
    assert einzelheit_passt(ansichten, (113, 36))      # Kanten der Kabelnut
    assert not einzelheit_passt(ansichten, (132, 72))  # samt entfernter Bezugspunkte: nur im Blattmaßstab


def test_sammelangaben_halten_platz_ueber_dem_schriftfeld_frei():
    from swki.zeichnung.blatt import RAND_MM
    sammel = 40.0
    for groessen in ({"haupt": (100, 60), "seite": (60, 60), "drauf": (100, 40)}, {"haupt": (300, 100)},
                     {"haupt": (170, 200)}):
        format_, massstab, plaetze = anordnen(groessen, sammel_mm=sammel)
        x0, y0, x1, y1 = zeichenfeld(format_)
        band = (x1 - SCHRIFTFELD_MM[0], y0 + SCHRIFTFELD_MM[1], x1, y0 + SCHRIFTFELD_MM[1] + sammel)
        for p in plaetze:
            assert not _ueberlappt(_rechteck(p), band), p
        _pruefe(format_, plaetze)


def test_sammel_mm_null_aendert_nichts():
    g = {"haupt": (100, 60), "seite": (60, 60), "drauf": (100, 40)}
    assert anordnen(g) == anordnen(g, sammel_mm=0.0)


def test_einzelheit_passt_mit_sammel_mm_nie_guenstiger():
    from swki.zeichnung.layout import einzelheit_passt
    g = {"haupt": (40, 50), "drauf": (40, 25)}
    assert einzelheit_passt(g, (10, 30)) is True          # ohne Reserve lohnt die Einzelheit
    assert einzelheit_passt(g, (10, 30), sammel_mm=40.0) is False  # mit Reserve ändert sich Format oder Maßstab
    for gr in ({"haupt": (120, 80), "drauf": (120, 40)}, g):
        for einzelheit in ((10, 10), (10, 30), (30, 20), (60, 40), (100, 80)):
            assert einzelheit_passt(gr, einzelheit, 40.0) <= einzelheit_passt(gr, einzelheit, 0.0)


def test_einzelheit_passt_false_statt_valueerror(monkeypatch):
    from swki.zeichnung import layout

    def kaputt(*a, **k):
        raise ValueError("passt nicht")
    monkeypatch.setattr(layout, "anordnen", kaputt)
    assert layout.einzelheit_passt({"haupt": (10, 10)}, (5, 5)) is False


def test_waehle_mit_sammel_mm():
    from swki.zeichnung.blatt import waehle
    assert waehle((100, 60)) == waehle((100, 60), 0.0)
    assert waehle((100, 190)) == ("A4", (1, 1))
    assert waehle((100, 190), 40.0) == ("A3quer", (1, 1))  # die Reserve verdrängt die Ansichten vom A4


def test_freiflaechen_mit_sammel_mm():
    from swki.zeichnung.blatt import freiflaechen
    ohne, mit = freiflaechen("A3quer"), freiflaechen("A3quer", sammel_mm=25.0)
    assert mit[0][1] == ohne[0][1] + 25.0 and mit[1] == ohne[1]
