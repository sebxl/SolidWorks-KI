"""Live: Notausgang (typ: skript) und Material/Eigenschaften (SolidWorks muss laufen)."""

import pytest

from swki.compiler.eigenschaften import lies_eigenschaften, setze_eigenschaften, setze_material

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def test_notausgang_skript(tmp_path):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "f2.py").write_text(
        "def bauen(ctx):\n"
        "    skizze, _ = ctx.skizze({'feature': 'f1', 'flaeche': '+y'},\n"
        "                           [{'kreis': {'mitte': [0, 0], 'durchmesser': 10}}])\n"
        "    ctx.auswahl_leeren()\n"
        "    skizze.Select2(False, 0)\n"
        "    return ctx.model.FeatureManager.FeatureCut4(\n"
        "        True, False, False, 0, 0, ctx.m(5), 0.0, False, False, False, False, 0.0, 0.0,\n"
        "        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False)\n",
        encoding="utf-8",
    )
    skript = {"id": "f2", "typ": "skript", "datei": "skripte/f2.py", "luecke": "Test des Notausgangs"}
    with gebautes_teil(_spec(skript), spec_pfad=tmp_path / "t.yaml") as (ctx, fehler, _):
        assert fehler is None
        assert ctx.ergebnis("f2").sw_name == "f2"
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - zylinder_mm3(10, 5), abs=1e-3)


def test_material_und_eigenschaften():
    with gebautes_teil(_spec()) as (ctx, fehler, _):
        assert fehler is None
        assert setze_material(ctx.app, ctx.model, "1.2312").startswith("1.2312 (")
        setze_eigenschaften(ctx.model, {"Benennung": "Formplatte DS – Test", "Auftrag": "A-1"})
        assert lies_eigenschaften(ctx.model) == {"Benennung": "Formplatte DS – Test", "Auftrag": "A-1"}
