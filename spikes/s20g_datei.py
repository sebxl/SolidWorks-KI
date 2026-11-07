"""Spike S20 g (Diagnose): gespeicherte Spannplatte öffnen (nur lesen) – Körper sichtbar, Ebenen sichtbar, Aufnahme.
Kein Produktionscode. Aufruf: .venv\\Scripts\\python.exe -m spikes.s20g_datei <pfad.SLDPRT> <bilderordner>"""

import json
import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

app = verbinde(lade_rechner().sw_jahr)
model = oeffne(app, Path(sys.argv[1]), sichtbar=True, nur_lesen=True)
try:
    koerper = [bool(b.Visible) for b in model.GetBodies2(0, False) or ()]
    f, ebenen = model.FirstFeature, []
    while f is not None:
        if f.GetTypeName2 == "RefPlane":
            ebenen.append((f.Name, f.Visible))
        f = f.GetNextFeature
    print(json.dumps({"koerper_sichtbar": koerper, "ebenen": ebenen}))
    print(screenshots(app, model, Path(sys.argv[2])))
finally:
    sw.schliesse(app, model)
