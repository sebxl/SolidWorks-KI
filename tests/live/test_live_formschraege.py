"""Live: Formschräge an Aufsatz und Schnitt (Paket Formschräge) – Volumen, Messung der Seitenflächen, Gleichung
(SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw
from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.pruefung.bewertung import formschraege_abweichungen
from swki.pruefung.messen import formschraegen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}
KREIS = {"kreis": {"mitte": [0, 0], "durchmesser": 20}}
TOL_WINKEL = 0.01


def _spec(*features, **parameter):
    return {"art": "teil", "name": "T", "parameter": {"W": 10, **parameter}, "features": [KLOTZ, *features]}


def _schraeg(typ: str, querschnitt: str, element=KREIS, ebene=DECKFLAECHE, ende_typ="blind", **ende) -> dict:
    tiefe = {"tiefe": 8} if ende_typ in ("blind", "mittig") else {}
    ende = {"typ": ende_typ, **tiefe, **ende, "formschraege": {"winkel": "=W", "querschnitt": querschnitt}}
    return {"id": "f2", "typ": typ, "skizze": {"ebene": ebene, "elemente": [element]}, "ende": ende}


def _pruefe(ctx, f: dict) -> None:
    ist = formschraegen(ctx, ctx.spec)[f["id"]]
    assert isinstance(ist, dict), ist
    assert ist["flaechen"], ist
    assert formschraege_abweichungen(f, ist, ctx.spec["parameter"], TOL_WINKEL) == [], ist


@pytest.mark.parametrize(("typ", "querschnitt"), [
    ("extrusion", "kleiner"), ("extrusion", "groesser"), ("schnitt", "kleiner"), ("schnitt", "groesser"),
])
def test_kreis_blind(typ, querschnitt):
    f = _schraeg(typ, querschnitt)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        v = volumen(querschnitt_koeffizienten(KREIS, {}), 8, 10, querschnitt)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + (v if typ == "extrusion" else -v), rel=1e-6)
        _pruefe(ctx, f)


def test_tasche_mit_eckradius_und_gleichung():
    element = {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 5}}
    f = _schraeg("schnitt", "kleiner", element)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        k = querschnitt_koeffizienten(element, {})
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(k, 8, 10, "kleiner"), rel=1e-6)
        _pruefe(ctx, f)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert '"D3@f2" = "W"' in texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"W" = 10'), '"W" = 15')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(k, 8, 15, "kleiner"), rel=1e-6)


def test_aufsatz_umgekehrt():
    # Skizze 12 mm über der Deckfläche, der Zapfen wächst nach unten bis auf die Deckfläche und verjüngt sich dabei
    f = _schraeg("extrusion", "kleiner", ebene={"versatz": {"ebene": "oben", "abstand": 32}}, tiefe=12, umkehren=True)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + volumen(querschnitt_koeffizienten(KREIS, {}), 12, 10, "kleiner"),
                                                       rel=1e-6)
        _pruefe(ctx, f)


def test_steg_mittig():
    # Steg frei über der Platte (y 34 … 46, z ± 4): zweiter Körper, dafür ist sein Volumen exakt bekannt
    element = {"rechteck": {"mitte": [0, 40], "breite": 40, "hoehe": 12}}
    f = _schraeg("extrusion", "kleiner", element, ebene="vorne", ende_typ="mittig")
    with gebautes_teil(_spec(f, W=5)) as (ctx, fehler, _):
        assert fehler is None
        v = volumen(querschnitt_koeffizienten(element, {}), 8, 5, "kleiner", mittig=True)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + v, rel=1e-6)
        _pruefe(ctx, f)


def test_trichter_durch_alles():
    f = _schraeg("schnitt", "groesser", ebene={"feature": "f1", "flaeche": "-y"}, ende_typ="durch_alles")
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(querschnitt_koeffizienten(KREIS, {}), 20, 10, "groesser"),
                                                       rel=1e-6)
        _pruefe(ctx, f)
