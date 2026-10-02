import copy

import pytest

from swki.pruefung.bewertung import bewerte
from swki.pruefung.messen import messe

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw
STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
SPEC = {"art": "teil", "name": "T", "parameter": {"d": 8, "D": 20, "h": 12}, "features": [
    {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [["=d/2", 0], ["=D/2", 0], ["=D/2", "=h"], ["=d/2", "=h"]]}},
        {"mittellinie": {"von": [0, 0], "bis": [0, 10]}}]}},
    {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
    {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}}],
    "pruefung": {
        "huellquader": ["=D", "=h", "=D"], "volumen": {"soll": "auto"},
        "masse_pruefen": [
            {"was": "h", "von": {"referenz": "EINBAU_EBENE"}, "zu": {"feature": "f1", "flaeche": "+y"}, "soll": "=h"}],
        "durchmesser_pruefen": [
            {"was": "d", "feature": "f1", "nahe": ["=d/2", "=h/2", 0], "soll": "=d", "referenz": "EINBAU_ACHSE"},
            {"was": "D", "feature": "f1", "nahe": ["=D/2", "=h/2", 0], "soll": "=D", "referenz": "EINBAU_ACHSE"}]}}


def test_durchmesser_und_referenzen_messen():
    with gebautes_teil(SPEC) as (ctx, fehler, _):
        assert fehler is None
        messwerte = messe(ctx)
    bericht = bewerte(SPEC, messwerte, STANDARD)
    assert bericht["bestanden"], bericht["maengel"]
    ids = {p["id"]: p["ok"] for p in bericht["pruefungen"]}
    assert all(ids[x] is True for x in ("durchmesser:d", "durchmesser:D", "mass:h", "huellquader", "volumen"))
    falsch = copy.deepcopy(SPEC)
    falsch["pruefung"]["durchmesser_pruefen"][0]["soll"] = "=d+0.1"
    assert [x["pruefung"] for x in bewerte(falsch, messwerte, STANDARD)["maengel"]] == ["durchmesser:d"]
