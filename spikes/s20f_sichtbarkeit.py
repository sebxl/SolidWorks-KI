"""Spike S20 f (Diagnose): nach welchem Feature der Spannplatte ist der Körper unsichtbar? Kein Produktionscode.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s20f_sichtbarkeit   (SolidWorks muss laufen)
"""

import json
from pathlib import Path

import yaml

from tests.live.bauhilfe import gebautes_teil

SPEC = yaml.safe_load(Path("tests/referenz/stil/spannplatte.yaml").read_text(encoding="utf-8"))


def _sichtbar(model) -> list:
    aus = []
    for b in model.GetBodies2(0, False) or ():
        try:
            aus.append(bool(b.Visible))
        except Exception as e:  # Late Binding: Property eventuell als Methode
            aus.append(repr(e))
    return aus


for n in range(1, len(SPEC["features"]) + 1):
    spec = {**SPEC, "features": SPEC["features"][:n]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        print(json.dumps({"bis": SPEC["features"][n - 1]["id"], "fehler": None if fehler is None else repr(fehler),
                          "sichtbar": _sichtbar(ctx.model),
                          "nur_sichtbare": len(ctx.model.GetBodies2(0, True) or ())}), flush=True)
