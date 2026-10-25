"""Referenz-Suite durch den Schnellbau (Spec C1 §4.2), ohne SolidWorks.

1. Jedes Referenzteil (tests/referenz/*/*.yaml, art teil) gegen die Sollwerte seiner eigenen pruefung (Hüllquader,
   Volumen soll/auto) – dieselben Werte, gegen die SolidWorks in der Live-Suite besteht.
2. Gegen die von SolidWorks gemessenen Werte in sw_referenz.json (werkzeuge/schnellbau_abgleich.py, live erzeugt).
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("build123d")

from swki.pruefung.geometrie import volumen_auto  # noqa: E402
from swki.pruefung.huellquader import huellquader_auto  # noqa: E402
from swki.schnellbau.fehler import NICHT_UNTERSTUETZT, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue, lade  # noqa: E402
from swki.spec.ausdruck import auswerten  # noqa: E402

REFERENZ = Path(__file__).parents[1] / "referenz"
SW_REFERENZ = Path(__file__).with_name("sw_referenz.json")
TEILE = sorted(p for p in REFERENZ.glob("*/*.yaml") if lade(p).get("art") == "teil")


def _name(p: Path) -> str:
    return f"{p.parent.name}/{p.stem}"


def _groesse(t) -> list[float]:
    bb = t.solid.bounding_box()
    return [bb.size.X, bb.size.Y, bb.size.Z]


@pytest.mark.parametrize("pfad", TEILE, ids=_name)
def test_referenzteil_wie_eigene_pruefung(pfad):
    spec = lade(pfad)
    if any(f["typ"] == "skript" for f in spec["features"]):
        with pytest.raises(SchnellbauFehler) as e:
            baue(spec)
        assert e.value.code == NICHT_UNTERSTUETZT
        return
    t = baue(spec)
    p = t.parameter
    pr = spec.get("pruefung", {})
    hq = pr.get("huellquader")
    if hq == "auto":
        hq, _ = huellquader_auto(spec)
    if hq is not None:
        assert _groesse(t) == pytest.approx([auswerten(x, p) for x in hq], abs=1e-3)
    vol = pr.get("volumen")
    if vol:
        soll = volumen_auto(spec)[0] if vol.get("soll") == "auto" else vol.get("soll")
        if soll is not None:
            assert t.solid.volume == pytest.approx(soll, rel=1e-4)


def _sw_werte() -> dict:
    return json.loads(SW_REFERENZ.read_text(encoding="utf-8")) if SW_REFERENZ.exists() else {}


@pytest.mark.parametrize("name", sorted(_sw_werte()) or ["(keine Werte)"])
def test_referenzteil_wie_solidworks(name):
    werte = _sw_werte()
    if not werte:
        pytest.skip("sw_referenz.json fehlt – werkzeuge/schnellbau_abgleich.py live laufen lassen")
    w = werte[name]
    t = baue(REFERENZ / w["spec"])
    assert t.solid.volume == pytest.approx(w["volumen"], rel=1e-6)
    assert _groesse(t) == pytest.approx(w["huellquader"], abs=1e-4)
