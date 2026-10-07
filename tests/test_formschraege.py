"""Reine Rechnung der Formschräge (swki.formschraege, ohne SolidWorks)."""

import math

import pytest

from swki.formschraege import (
    extrusionsrichtung, feste_tiefe, grenze_kleiner, quer_zur_richtung, querschnitt_koeffizienten, schraege,
    seitenflaechen, skizzennormale, soll_vorzeichen, volumen, volumen_feature,
)


def _feature(element, ende, typ="extrusion"):
    return {"id": "f2", "typ": typ, "skizze": {"ebene": "oben", "elemente": [element]}, "ende": ende}


def test_schraege_nur_bei_extrusion_und_schnitt():
    s = {"winkel": 5, "querschnitt": "kleiner"}
    assert schraege(_feature({"kreis": {}}, {"typ": "blind", "tiefe": 5, "formschraege": s})) == s
    assert schraege(_feature({"kreis": {}}, {"typ": "blind", "tiefe": 5})) is None
    assert schraege({"id": "r", "typ": "rotation", "skizze": {}}) is None


@pytest.mark.parametrize(("ebene", "normale"), [
    ("oben", (0.0, 1.0, 0.0)),
    ({"versatz": {"ebene": "rechts", "abstand": 20}}, (1.0, 0.0, 0.0)),
    ({"feature": "f1", "flaeche": "-y"}, (0.0, -1.0, 0.0)),
    ({"nahe": [0, 0, 0]}, None),
])
def test_skizzennormale(ebene, normale):
    assert skizzennormale(ebene) == normale


@pytest.mark.parametrize(("typ", "umkehren", "r"), [
    ("extrusion", False, (0.0, 1.0, 0.0)),
    ("extrusion", True, (0.0, -1.0, 0.0)),
    ("schnitt", False, (0.0, -1.0, 0.0)),
    ("schnitt", True, (0.0, 1.0, 0.0)),
])
def test_extrusionsrichtung_wie_handler(typ, umkehren, r):
    assert extrusionsrichtung((0.0, 1.0, 0.0), typ, umkehren) == r


@pytest.mark.parametrize(("typ", "querschnitt", "vorzeichen"), [
    ("extrusion", "kleiner", 1), ("extrusion", "groesser", -1), ("schnitt", "kleiner", -1), ("schnitt", "groesser", 1),
])
def test_soll_vorzeichen(typ, querschnitt, vorzeichen):
    assert soll_vorzeichen(typ, querschnitt) == vorzeichen


def test_quer_zur_richtung():
    assert quer_zur_richtung("+x", (0.0, 1.0, 0.0))
    assert quer_zur_richtung("-z", (0.0, 1.0, 0.0))
    assert not quer_zur_richtung("+y", (0.0, 1.0, 0.0))
    assert not quer_zur_richtung("-y", (0.0, 1.0, 0.0))


def test_feste_tiefe():
    p = {"T": 12}
    assert feste_tiefe({"typ": "blind", "tiefe": "=T"}, p) == 12
    assert feste_tiefe({"typ": "mittig", "tiefe": "=T"}, p) == 6
    assert feste_tiefe({"typ": "durch_alles"}, p) is None
    assert feste_tiefe({"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}}, p) is None


def test_grenze_kleiner():
    assert grenze_kleiner({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {}) == (10, "halber Durchmesser")
    assert grenze_kleiner({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {}) == (15, "halbe kürzere Seite")
    assert grenze_kleiner({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 4}}, {}) == (4, "Eckradius")
    assert grenze_kleiner({"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 8}}, {}) == (4, "halbe Breite")
    assert grenze_kleiner({"polygon": {"punkte": [[0, 0], [10, 0], [0, 10]]}}, {}) is None


def _flaeche_versetzt(element, d: float) -> float:
    a, p, k = querschnitt_koeffizienten(element, {})
    return a + p * d + k * d * d


def test_koeffizienten_rechteck_kreis_langloch():
    assert _flaeche_versetzt({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, 2) == pytest.approx(44 * 34)
    assert _flaeche_versetzt({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, -3) == pytest.approx(math.pi * 49)
    r = {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 5}}
    assert _flaeche_versetzt(r, -2) == pytest.approx(36 * 26 - (4 - math.pi) * 9)
    langloch = {"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 10}}
    assert _flaeche_versetzt(langloch, 1) == pytest.approx(30 * 12 + math.pi * 36)


def test_koeffizienten_polygon():
    rho = 10.0  # Inkreisradius eines regelmäßigen Sechsecks
    ecken = [(2 * rho / math.sqrt(3) * math.cos(math.radians(60 * k)), 2 * rho / math.sqrt(3) * math.sin(math.radians(60 * k)))
             for k in range(6)]
    sechseck = {"polygon": {"punkte": [list(e) for e in ecken]}}
    assert _flaeche_versetzt(sechseck, 2) == pytest.approx(2 * math.sqrt(3) * 12**2)
    quadrat = {"polygon": {"punkte": [[0, 0], [0, 10], [10, 10], [10, 0]]}}  # im Uhrzeigersinn
    assert _flaeche_versetzt(quadrat, -1) == pytest.approx(64)
    assert querschnitt_koeffizienten({"polygon": {"punkte": [[0, 0], [10, 0], [10, 10]], "radien": 2}}, {}) is None
    konkav = {"polygon": {"punkte": [[0, 0], [10, 0], [10, 10], [5, 3], [0, 10]]}}
    assert querschnitt_koeffizienten(konkav, {}) is None
    kontur = {"kontur": {"start": [0, 0], "segmente": [{"linie": [10, 0]}, {"linie": [0, 0]}]}}
    assert querschnitt_koeffizienten(kontur, {}) is None


def test_volumen_kegelstumpf_und_prismatoid():
    t = math.tan(math.radians(15))
    r1, r2 = 10, 10 - 12 * t
    kreis = querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {})
    assert volumen(kreis, 12, 15, "kleiner") == pytest.approx(math.pi * 12 / 3 * (r1 * r1 + r1 * r2 + r2 * r2))
    rechteck = querschnitt_koeffizienten({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {})
    d = 8 * math.tan(math.radians(10))
    a1, am, a2 = 40 * 30, (40 + d) * (30 + d), (40 + 2 * d) * (30 + 2 * d)
    assert volumen(rechteck, 8, 10, "groesser") == pytest.approx(8 / 6 * (a1 + 4 * am + a2))


def test_volumen_mittig_zwei_haelften():
    k = querschnitt_koeffizienten({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {})
    assert volumen(k, 20, 5, "kleiner", mittig=True) == pytest.approx(2 * volumen(k, 10, 5, "kleiner"))


def test_volumen_feature():
    s = {"winkel": "=W", "querschnitt": "kleiner"}
    f = _feature({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {"typ": "blind", "tiefe": 12, "formschraege": s})
    v, grund = volumen_feature(f, {"W": 15})
    assert grund == "analytisch"
    kreis = querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {})
    assert v == pytest.approx(volumen(kreis, 12, 15, "kleiner"))
    f["ende"] = {"typ": "durch_alles", "formschraege": s}
    assert volumen_feature(f, {"W": 15}) == (None, "f2: ende durch_alles mit Formschräge (Tiefe hängt von der Geometrie ab)")
    f["ende"] = {"typ": "blind", "tiefe": 12, "formschraege": s}
    f["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 8}})
    assert volumen_feature(f, {"W": 15})[0] is None


def _normale(winkel: float, nach_oben: bool) -> tuple[float, float, float]:
    """Äußere Normale einer um winkel geneigten Seitenwand mit Blick nach +x; r = +y."""
    a = math.radians(winkel)
    return (math.cos(a), math.sin(a) if nach_oben else -math.sin(a), 0.0)


def test_seitenflaechen_ohne_deckflaechen():
    r = (0.0, 1.0, 0.0)
    messungen = [((10.0, 5.0, 0.0), _normale(15, True)), ((0.0, 12.0, 0.0), (0.0, 1.0, 0.0)),
                 ((0.0, 0.0, 0.0), (0.0, -1.0, 0.0)), ((-10.0, 5.0, 0.0), _normale(15, False))]
    assert seitenflaechen(messungen, r) == [{"winkel": pytest.approx(15), "vorzeichen": 1},
                                            {"winkel": pytest.approx(15), "vorzeichen": -1}]


def test_seitenflaechen_gerade_wand():
    assert seitenflaechen([((10.0, 5.0, 0.0), (1.0, 0.0, 0.0))], (0.0, 1.0, 0.0)) == [{"winkel": 0.0, "vorzeichen": 0}]


def test_seitenflaechen_mittig_misst_je_seite_von_der_ebene_weg():
    r = (0.0, 1.0, 0.0)
    oben = ((10.0, 4.0, 0.0), _normale(5, True))  # verjüngt sich nach +y
    unten = ((10.0, -4.0, 0.0), _normale(5, False))  # verjüngt sich nach −y
    assert [x["vorzeichen"] for x in seitenflaechen([oben, unten], r, (0.0, 0.0, 0.0))] == [1, 1]
    assert [x["vorzeichen"] for x in seitenflaechen([oben, unten], r)] == [1, -1]
