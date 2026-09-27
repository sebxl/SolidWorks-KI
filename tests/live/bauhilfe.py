"""Hilfen für Live-Tests der Handler: Minimalteil bauen, messen, wieder schließen."""

import math
from contextlib import contextmanager
from pathlib import Path

from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner
from swki.verbindung import in_mm3, verbinde


@contextmanager
def gebautes_teil(spec: dict, spec_pfad: Path = Path("live.yaml")):
    """Baut spec in einem neuen Teil; liefert (ctx, fehler, protokoll). Das Teil wird immer geschlossen."""
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, spec_pfad, 0.1)
        globale_variablen(model, spec.get("parameter", {}))
        protokoll = Protokoll("live", "live.yaml", 0, r.sw_jahr)
        fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        yield ctx, fehler, protokoll
    finally:
        sw.schliesse(app, model)


def volumen_mm3(model) -> float:
    return in_mm3(model.Extension.CreateMassProperty.Volume)


def zylinder_mm3(d: float, h: float) -> float:
    return math.pi * (d / 2) ** 2 * h
