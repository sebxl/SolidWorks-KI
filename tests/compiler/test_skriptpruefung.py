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
    ],
)
def test_verbotenes_wird_gemeldet(quelle, teil):
    befunde = pruefe_skript(quelle)
    assert any(teil in b["meldung"] for b in befunde), befunde


def test_zeilennummer():
    befunde = pruefe_skript("def bauen(ctx):\n    x = 1\n    eval('2')\n")
    assert befunde == [{"zeile": 3, "meldung": "'eval' ist nicht erlaubt"}]


def test_bauen_fehlt():
    assert pruefe_skript("def machen(ctx):\n    pass\n") == [{"zeile": 0, "meldung": "Funktion 'def bauen(ctx)' fehlt"}]


def test_syntaxfehler():
    [befund] = pruefe_skript("def bauen(ctx)\n    pass\n")
    assert befund["zeile"] == 1 and befund["meldung"].startswith("Syntaxfehler")
