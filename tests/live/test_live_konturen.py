"""Live: runde Konturen in Skizzen – Eckradius, konkave Ecke, Langloch, Kontur mit Bögen (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw

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


@pytest.mark.parametrize(("winkel", "box"), [
    (0, [-9, 0, -9, 29, 10, -1]),     # oben: X = u, Z = −v
    (90, [6, 0, -24, 14, 10, 14]),
    (30, None),
])
def test_langloch(winkel, box):
    spec = _platte({"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": winkel}})
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx((30 * 8 + 16 * math.pi) * 10, abs=1e-3)
        ist = sw.teilebox_mm(ctx.model)
        if box is not None:
            assert ist == pytest.approx(box, abs=1e-6)
        else:  # schräg: Mitte bleibt (X 10, Z −5), Ausdehnung in X = 30·cos 30° + 8
            assert ((ist[0] + ist[3]) / 2, (ist[2] + ist[5]) / 2) == pytest.approx((10, -5), abs=1e-6)
            assert ist[3] - ist[0] == pytest.approx(30 * math.cos(math.radians(30)) + 8, abs=1e-6)


@pytest.mark.parametrize(("ebene", "box"), [
    ("oben", [-50, 0, -45, 50, 10, -25]),     # X = u, Z = −v
    ("vorne", [-50, 25, 0, 50, 45, 10]),      # X = u, Y = v
    ("rechts", [0, 25, -50, 10, 45, 50]),     # Z = −u, Y = v
])
def test_kontur_mit_boegen(ebene, box):
    with gebautes_teil(_platte({"kontur": KONTUR}, ebene=ebene)) as (ctx, fehler, _):
        assert fehler is None
        # Bögen gegen den Uhrzeigersinn in (u, v) wölben sich nach außen: Fläche 80·20 + π·10²
        assert volumen_mm3(ctx.model) == pytest.approx((1600 + 100 * math.pi) * 10, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx(box, abs=1e-6)
