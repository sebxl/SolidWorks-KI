import pytest

from swki.compiler.topologie import referenz_geometrie

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw


def test_referenzen_achse_und_ebenen():
    spec = {"art": "teil", "name": "T", "parameter": {"h": 20}, "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}]}, "ende": {"typ": "blind", "tiefe": "=h"}},
        {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
        {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
        {"id": "EINBAU_EBENE_2", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=h"}},
    ]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        art, punkt, richtung = referenz_geometrie(ctx.model.FeatureByName("EINBAU_ACHSE"))
        assert art == "achse" and abs(richtung[1]) == pytest.approx(1)
        assert punkt[0] == pytest.approx(0, abs=1e-6) and punkt[2] == pytest.approx(0, abs=1e-6)
        art, punkt, normale = referenz_geometrie(ctx.model.FeatureByName("EINBAU_EBENE"))
        assert art == "ebene" and abs(normale[1]) == pytest.approx(1) and punkt[1] == pytest.approx(0, abs=1e-6)
        art, punkt, normale = referenz_geometrie(ctx.model.FeatureByName("EINBAU_EBENE_2"))
        assert art == "ebene" and abs(normale[1]) == pytest.approx(1) and punkt[1] == pytest.approx(20, abs=1e-6)
        assert ctx.ergebnis("EINBAU_EBENE_2").richtung == pytest.approx((0, 1, 0))
