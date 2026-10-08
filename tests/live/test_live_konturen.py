"""Live: runde Konturen in Skizzen – Eckradius, konkave Ecke, Langloch, Kontur mit Bögen (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
KONTUR = {"start": [-40, 25], "segmente": [
    {"linie": [40, 25]}, {"bogen": [40, 45], "mitte": [40, 35]},
    {"linie": [-40, 45]}, {"bogen": [-40, 25], "mitte": [-40, 35]},
]}


def _platte(element, ebene="oben", parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {}, "features": [{
        "id": "f1", "typ": "extrusion", "skizze": {"ebene": ebene, "elemente": [element]},
        "ende": {"typ": "blind", "tiefe": 10},
    }]}


def _gleichungen(model) -> list[str]:
    g = model.GetEquationMgr
    return [g.Equation(i) for i in range(g.GetCount)]


def _setze(model, alt: str, neu: str) -> None:
    """Gleichung ersetzen (Property-Put nur per Invoke, S9a), auswerten, neu aufbauen."""
    g = model.GetEquationMgr
    dispid = g._oleobj_.GetIDsOfNames("Equation")
    g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, _gleichungen(model).index(alt), neu)
    g.EvaluateAll
    sw.rebuild(model)


def test_rechteck_mit_eckradius_haengt_an_parametern():
    spec = _platte({"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60, "radius": "=R"}},
                   parameter={"L": 100, "R": 6})
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-50, 0, -30, 50, 10, 30], abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((6000 - (4 - math.pi) * 36) * 10, abs=1e-3)
        assert sum(1 for t in _gleichungen(ctx.model) if t.endswith('= "R"')) == 4  # je Ecke ein Radiusmaß
        _setze(ctx.model, '"R" = 6', '"R" = 8')
        _setze(ctx.model, '"L" = 100', '"L" = 120')
        assert sw.teilebox_mm(ctx.model)[0:4:3] == pytest.approx([-60, 60], abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((7200 - (4 - math.pi) * 64) * 10, abs=1e-3)


def test_polygon_mit_konvexen_und_konkaver_ecke():
    punkte = [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]]
    spec = _platte({"polygon": {"punkte": punkte, "radien": [3, 3, 3, 5, 3, 3]}}, ebene="vorne")
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        erwartet = (1200 - 5 * (9 - 9 * math.pi / 4) + (25 - 25 * math.pi / 4)) * 10
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx([0, 0, 0, 40, 40, 10], abs=1e-6)


def test_mehrere_langloecher_in_einer_skizze():
    """Vier Langlöcher in einer Skizze (AP 6.8 Durchlicht): GetSketchSegments liefert nicht in Erzeugungsreihenfolge."""
    spec = _platte({"langloch": {"mitte": [-30, 20], "laenge": 4, "breite": 5, "winkel": 0}})
    spec["features"][0]["skizze"]["elemente"] += [
        {"langloch": {"mitte": [30, 20], "laenge": 4, "breite": 5, "winkel": 0}},
        {"langloch": {"mitte": [30, -20], "laenge": 4, "breite": 5, "winkel": 0}},
        {"langloch": {"mitte": [-30, -20], "laenge": 4, "breite": 5, "winkel": 0}},
    ]
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(4 * (4 * 5 + 2.5 ** 2 * math.pi) * 10, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-34.5, 0, -22.5, 34.5, 10, 22.5], abs=1e-6)


@pytest.mark.parametrize(("winkel", "box"), [
    (0, [-9, 0, -9, 29, 10, -1]),     # oben: X = u, Z = −v
    (90, [6, 0, -24, 14, 10, 14]),
    (30, None),                       # schräg: alle Maße an Parametern (Parametrik, Spec §4)
])
def test_langloch(winkel, box):
    if box is None:
        spec = _platte({"langloch": {"mitte": ["=MU", 5], "laenge": "=LL", "breite": "=LB", "winkel": "=W"}},
                       parameter={"MU": 10, "LL": 30, "LB": 8, "W": winkel})
    else:
        spec = _platte({"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": winkel}})
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx((30 * 8 + 16 * math.pi) * 10, abs=1e-3)
        ist = sw.teilebox_mm(ctx.model)
        if box is not None:
            assert ist == pytest.approx(box, abs=1e-6)
            return
        # schräg: Mitte bleibt (X 10, Z −5), Ausdehnung in X = 30·cos 30° + 8
        assert ((ist[0] + ist[3]) / 2, (ist[2] + ist[5]) / 2) == pytest.approx((10, -5), abs=1e-6)
        assert ist[3] - ist[0] == pytest.approx(30 * math.cos(math.radians(30)) + 8, abs=1e-6)
        assert sum(1 for t in _gleichungen(ctx.model) if t.endswith(('= "LL"', '= "LB"', '= "W"', '= "MU"'))) >= 4
        # Parameter ändern: Länge, Breite, Winkel und Lage der Mitte folgen
        _setze(ctx.model, '"LL" = 30', '"LL" = 40')
        _setze(ctx.model, '"LB" = 8', '"LB" = 6')
        _setze(ctx.model, '"W" = 30', '"W" = 45')
        _setze(ctx.model, '"MU" = 10', '"MU" = 15')
        assert volumen_mm3(ctx.model) == pytest.approx((40 * 6 + 9 * math.pi) * 10, abs=1e-3)
        ist = sw.teilebox_mm(ctx.model)
        assert ((ist[0] + ist[3]) / 2, (ist[2] + ist[5]) / 2) == pytest.approx((15, -5), abs=1e-6)
        assert ist[3] - ist[0] == pytest.approx(40 * math.cos(math.radians(45)) + 6, abs=1e-6)
        assert ist[5] - ist[2] == pytest.approx(40 * math.sin(math.radians(45)) + 6, abs=1e-6)


KONTUR_PARAMETRISCH = {"start": ["=-KB/2", "=KV"], "segmente": [
    {"linie": ["=KB/2", "=KV"]}, {"bogen": ["=KB/2", "=KV+KH"], "mitte": ["=KB/2", "=KV+KH/2"]},
    {"linie": ["=-KB/2", "=KV+KH"]}, {"bogen": ["=-KB/2", "=KV"], "mitte": ["=-KB/2", "=KV+KH/2"]},
]}


@pytest.mark.parametrize(("ebene", "box"), [
    ("oben", [-50, 0, -45, 50, 10, -25]),     # X = u, Z = −v; parametrisch (KB, KV, KH wie in der Referenz)
    ("vorne", [-50, 25, 0, 50, 45, 10]),      # X = u, Y = v
    ("rechts", [0, 25, -50, 10, 45, 50]),     # Z = −u, Y = v
])
def test_kontur_mit_boegen(ebene, box):
    parametrisch = ebene == "oben"
    spec = (_platte({"kontur": KONTUR_PARAMETRISCH}, ebene=ebene, parameter={"KB": 80, "KV": 25, "KH": 20})
            if parametrisch else _platte({"kontur": KONTUR}, ebene=ebene))
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        # Bögen gegen den Uhrzeigersinn in (u, v) wölben sich nach außen: Fläche 80·20 + π·10²
        assert volumen_mm3(ctx.model) == pytest.approx((1600 + 100 * math.pi) * 10, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx(box, abs=1e-6)
        if parametrisch:
            _setze(ctx.model, '"KB" = 80', '"KB" = 100')  # Mittenabstand der Bögen wächst, Höhe bleibt
            assert volumen_mm3(ctx.model) == pytest.approx((2000 + 100 * math.pi) * 10, abs=1e-3)
            assert sw.teilebox_mm(ctx.model) == pytest.approx([-60, 0, -45, 60, 10, -25], abs=1e-6)
            _setze(ctx.model, '"KH" = 20', '"KH" = 30')  # Höhe und damit Bogenradius wachsen
            assert volumen_mm3(ctx.model) == pytest.approx((3000 + 225 * math.pi) * 10, abs=1e-3)
            assert sw.teilebox_mm(ctx.model) == pytest.approx([-65, 0, -55, 65, 10, -25], abs=1e-6)


# --- Flächen mit negativer Normale: die Abbildung (u, v) → Skizze kehrt den Drehsinn um (Befund W1) ---

KLOTZ = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}}  # X ±50, Y 0…20, Z ±30
VOLL = 100 * 60 * 20


def _auf_flaeche(element, flaeche: str, tiefe: float = 5) -> dict:
    """Grundklotz und ein Schnitt `tiefe` mm tief in das Material, Skizze auf der Fläche {f1, flaeche}."""
    schnitt = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": flaeche},
                                                         "elemente": [element]},
               "ende": {"typ": "blind", "tiefe": tiefe}}
    return {"art": "teil", "name": "T", "parameter": {}, "features": [KLOTZ, schnitt]}


def _zylinder_lagen(ctx) -> list[tuple[float, float, float]]:
    """Achsenlagen (mm) der Zylinderflächen des Schnitts, nach (x, y, z) sortiert. Die Koordinate entlang der Achse
    ist beliebig (Ursprung der Zylinderfläche) und wird auf 0 gesetzt."""
    lagen = []
    for f in flaechen(ctx.ergebnis("f2").features[0]):
        if f.art == "zylinder":
            lagen.append(tuple(round(0.0 if abs(a) > 0.5 else p, 6) for p, a in zip(f.punkt, f.achse)))
    return sorted(lagen)


def _flach(lagen) -> list[float]:
    return [c for lage in lagen for c in lage]


@pytest.mark.parametrize(("flaeche", "kontur", "flaecheninhalt", "mitten"), [
    # Unterseite: Skizzensystem gespiegelt, (u, v) → X = u, Z = −v; Bogenmitten bei u = −25 und 35, v = 5 → Z = −5
    ("-y", {"start": [-25, -5], "segmente": [
        {"linie": [35, -5]}, {"bogen": [35, 15], "mitte": [35, 5]},
        {"linie": [-25, 15]}, {"bogen": [-25, -5], "mitte": [-25, 5]}]},
     60 * 20 + 100 * math.pi, [(-25, 0, -5), (35, 0, -5)]),
    # Rückseite: (u, v) → X = u, Y = v, Normale −z, Skizzensystem ebenfalls gespiegelt
    ("-z", {"start": [-25, 5], "segmente": [
        {"linie": [35, 5]}, {"bogen": [35, 15], "mitte": [35, 10]},
        {"linie": [-25, 15]}, {"bogen": [-25, 5], "mitte": [-25, 10]}]},
     60 * 10 + 25 * math.pi, [(-25, 10, 0), (35, 10, 0)]),
], ids=["unterseite", "rueckseite"])
def test_kontur_mit_boegen_auf_flaeche_mit_negativer_normale(flaeche, kontur, flaecheninhalt, mitten):
    with gebautes_teil(_auf_flaeche({"kontur": kontur}, flaeche)) as (ctx, fehler, _):
        assert fehler is None
        # Bögen gegen den Uhrzeigersinn in (u, v) wölben sich nach außen; der Gegenbogen gäbe die Fläche abzüglich der Halbkreise
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - flaecheninhalt * 5, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-50, 0, -30, 50, 20, 30], abs=1e-6)
        assert _flach(_zylinder_lagen(ctx)) == pytest.approx(_flach(mitten), abs=1e-6)


@pytest.mark.parametrize(("winkel", "flaeche"), [
    (150, "+y"),   # Winkel in [90°, 180) auf gleichsinniger Fläche
    (120, "+y"),
    (150, "-y"),   # … und auf gespiegelter Fläche
    (30, "-y"),
], ids=["150-oben", "120-oben", "150-unten", "30-unten"])
def test_langloch_winkel_ueber_90_grad_lage_der_bogenmitten(winkel, flaeche):
    spec = _auf_flaeche({"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": winkel}}, flaeche)
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - (30 * 8 + 16 * math.pi) * 5, abs=1e-3)
        # 30° und 150° haben dieselbe Box: die Lage der Bogenmitten (Modell: X = u, Z = −v) entscheidet
        halb = 15 * math.cos(math.radians(winkel)), 15 * math.sin(math.radians(winkel))
        erwartet = sorted((round(10 + s * halb[0], 6), 0, round(-(5 + s * halb[1]), 6)) for s in (-1, 1))
        assert _flach(_zylinder_lagen(ctx)) == pytest.approx(_flach(erwartet), abs=1e-6)
