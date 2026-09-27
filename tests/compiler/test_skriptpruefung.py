import pytest

from swki.compiler.skriptpruefung import pruefe_skript

GUT = """
import math


def bauen(ctx):
    skizze, _ = ctx.skizze({"feature": "f1", "flaeche": "+y"}, [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}])
    ctx.auswahl_leeren()
    skizze.Select2(False, 0)
    tiefe = ctx.m(5) * math.sqrt(2)
    return ctx.model.FeatureManager.FeatureCut4(
        True, False, False, 0, 0, tiefe, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False)
"""


def test_zulaessiges_skript():
    assert pruefe_skript(GUT) == []


@pytest.mark.parametrize(
    ("quelle", "teil"),
    [
        ("import os\ndef bauen(ctx):\n    pass\n", "'os'"),
        ("from shutil import rmtree\ndef bauen(ctx):\n    pass\n", "'shutil'"),
        ("import subprocess as sp\ndef bauen(ctx):\n    pass\n", "'subprocess'"),
        ("def bauen(ctx):\n    eval('1')\n", "'eval'"),
        ("def bauen(ctx):\n    open('x', 'w')\n", "'open'"),
        ("def bauen(ctx):\n    ctx.__class__\n", "Dunder"),
        ("def bauen(ctx):\n    ctx.model.SaveAs3('x', 0, 1)\n", "'SaveAs3'"),
        ("def bauen(ctx):\n    ctx.app.CloseDoc('x')\n", "'CloseDoc'"),
        ("def bauen(ctx):\n    getattr(ctx, 'app')\n", "'getattr'"),
        ("def bauen(ctx):\n    ctx.model.SaveAs4('x', 0, 0, None, None)\n", "'SaveAs4'"),
        ("def bauen(ctx):\n    ctx.model.saveas3('x', 0, 0)\n", "'saveas3'"),
        ("def bauen(ctx):\n    ctx.model.SaveSilent()\n", "'SaveSilent'"),
        ("def bauen(ctx):\n    ctx.app.CloseAndReopen(ctx.model, 0, None)\n", "'CloseAndReopen'"),
        ("def bauen(ctx):\n    ctx.model.Close()\n", "'Close'"),
        ("def bauen(ctx):\n    ctx.app.ActivateDoc3('x', False, 0, None)\n", "'ActivateDoc3'"),
        ("def bauen(ctx):\n    __builtins__['__import__']('os')\n", "Dunder"),
        ("def bauen(ctx):\n    __import__('os')\n", "'__import__'"),
    ],
)
def test_verbotenes_wird_gemeldet(quelle, teil):
    befunde = pruefe_skript(quelle)
    assert any(teil in b["meldung"] for b in befunde), befunde


REFERENZ_F10_GEWINDE = '''"""Gewindebohrungen M8 über den Bohrungsassistenten.

Notausgang: Gewinde bildet das Spezifikationsformat in Stufe 2 noch nicht ab. Aufrufkette aus Spike S9b (Baustein 21).
"""

SW_WZD_TAP = 4  # swWzdGeneralHoleTypes_e
SW_STANDARD_ISO = 8  # swWzdHoleStandards_e
SW_ISO_TAPPED_HOLE = 147  # swWzdHoleStandardFastenerTypes_e
SW_SEL_FACES = 2  # swSelectType_e
POSITIONEN = [(-100, 0), (100, 0)]  # (u, v) auf der Deckfläche wie in der Spezifikation


def bauen(ctx):
    deckflaeche = ctx.ebene({"feature": "f1", "flaeche": "+y"})
    features = []
    for u, v in POSITIONEN:
        x, y, z = ctx.modellpunkt_m(deckflaeche, u, v)
        ctx.auswahl_leeren()
        ctx.model.Extension.SelectByRay(x, y + 0.01, z, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, False, 0, 0)
        features.append(ctx.model.FeatureManager.HoleWizard5(
            SW_WZD_TAP, SW_STANDARD_ISO, SW_ISO_TAPPED_HOLE, "M8", 0, -1, 0.016, -1,  # blind 16, Durchmesser -1 = Norm
            0.012, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1,  # Gewindetiefe 12, kosmetisches Gewinde
            "", False, False, True, False, True, False,
        ))
        ctx.punkte_festlegen(features[-1], {"feature": "f1", "flaeche": "+y"}, [(u, v)])  # Lage voll bestimmen
    return features
'''


def test_referenzskript_formplatte_bleibt_zulaessig():
    assert pruefe_skript(REFERENZ_F10_GEWINDE) == []


def test_zeilennummer():
    befunde = pruefe_skript("def bauen(ctx):\n    x = 1\n    eval('2')\n")
    assert befunde == [{"zeile": 3, "meldung": "'eval' ist nicht erlaubt"}]


def test_bauen_fehlt():
    assert pruefe_skript("def machen(ctx):\n    pass\n") == [{"zeile": 0, "meldung": "Funktion 'def bauen(ctx)' fehlt"}]


def test_syntaxfehler():
    [befund] = pruefe_skript("def bauen(ctx)\n    pass\n")
    assert befund["zeile"] == 1 and befund["meldung"].startswith("Syntaxfehler")
