"""Live: lineares Muster, Kreismuster, Spiegeln (SolidWorks muss laufen)."""

import pytest

from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20
BOHRUNG = {
    "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
    "positionen": [[-40, 20]], "durchmesser": 8, "durch": True,
}


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def _achsen_xz(feature) -> list[tuple[float, float]]:
    return sorted((round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder")


def test_muster_linear_zwei_richtungen():
    saat = {**BOHRUNG, "positionen": [[-40, -20]]}  # Modell X=-40, Z=+20
    muster = {"id": "f3", "typ": "muster_linear", "features": ["f2"],
              "richtung1": {"achse": "x", "abstand": 20, "anzahl": 4},
              "richtung2": {"achse": "z", "abstand": 15, "anzahl": 2, "umkehren": True}}
    with gebautes_teil(_spec(saat, muster)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 8 * zylinder_mm3(8, 20), abs=1e-3)
        # Richtung 1 nach +X, Richtung 2 umgekehrt nach -Z; das Muster-Feature enthält nur die 7 neuen Instanzen
        assert _achsen_xz(ctx.ergebnis("f3").features[0]) == sorted(
            (x, z) for x in (-40.0, -20.0, 0.0, 20.0) for z in (20.0, 5.0) if (x, z) != (-40.0, 20.0)
        )


def test_muster_kreis():
    scheibe = {
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 100}}]},
        "ende": {"typ": "blind", "tiefe": 10},
    }
    loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
            "positionen": [[30, 0]], "durchmesser": 8, "durch": True}
    muster = {"id": "f3", "typ": "muster_kreis", "features": ["f2"], "achse": "y", "anzahl": 6}
    spec = {"art": "teil", "name": "T", "features": [scheibe, loch, muster]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(zylinder_mm3(100, 10) - 6 * zylinder_mm3(8, 10), abs=1e-3)


def test_spiegeln_an_ebene_vorne():
    spiegeln = {"id": "f3", "typ": "spiegeln", "features": ["f2"], "ebene": "vorne"}
    with gebautes_teil(_spec(BOHRUNG, spiegeln)) as (ctx, fehler, _):
        assert fehler is None
        assert _achsen_xz(ctx.ergebnis("f3").features[0]) == [(-40.0, 20.0)]
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 2 * zylinder_mm3(8, 20), abs=1e-3)
