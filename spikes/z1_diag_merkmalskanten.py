"""Diagnose Z1.3 Stufe 2 (Nutzer 18.11.2026: Einzelheit nur vergrößert, R-Pfeil auf den Bogen): Sichtbare Kanten einer
Zeichenansicht je Feature in Blattkoordinaten – über ihre Flächen (`IFace2.GetFeature`) und `IView.ModelToViewTransform`.
Für Bögen Mittelpunkt, Radius, Anfang/Ende. Dazu je Radiusmaß die Linien aus `IDisplayData`. Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_merkmalskanten <zeichnung.SLDDRW> <ansicht>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import _ruf, _umriss_mm

SW_DOC_DRAWING = 3
KANTE = 1


def main(pfad: Path, ansicht: str) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    mu = mathutil(app)
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        print("Umriss", [round(x, 1) for x in _umriss_mm(v)], "Position",
              [round(x * 1000, 1) for x in list(_ruf(v, "Position"))[:2]], "Maßstab", _ruf(v, "ScaleDecimal"))
        t = _ruf(v, "ModelToViewTransform")

        def blatt(p_m):
            q = mu.CreatePoint(r8_array(list(p_m))).MultiplyTransform(t).ArrayData
            return round(q[0] * 1000, 1), round(q[1] * 1000, 1)

        je = {}
        for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
            namen = set()
            for fl in list(_ruf(k, "GetTwoAdjacentFaces2") or ()):
                if fl is not None:
                    namen.add(_ruf(_ruf(fl, "GetFeature"), "Name"))
            c = _ruf(k, "GetCurve")
            cp = _ruf(k, "GetCurveParams3")
            a, e = blatt(_ruf(cp, "StartPoint")), blatt(_ruf(cp, "EndPoint"))
            bogen = None
            if _ruf(c, "IsCircle"):
                cx, cy, cz, *_, r = list(_ruf(c, "CircleParams"))
                bogen = (blatt((cx, cy, cz)), round(r * 1000, 2))
            for n in namen:
                je.setdefault(n, []).append((a, e, bogen))
        for n, kanten in sorted(je.items()):
            xs = [p[0] for a, e, _ in kanten for p in (a, e)]
            ys = [p[1] for a, e, _ in kanten for p in (a, e)]
            print(f"{n:16s} {len(kanten):3d} Kanten, Blatt-Box x {min(xs)}–{max(xs)}, y {min(ys)}–{max(ys)}")
            for a, e, bogen in kanten:
                if bogen:
                    print("      Bogen", "Mitte", bogen[0], "R", bogen[1], "von", a, "bis", e)
        for dd in _anzeige(v):
            if _ruf(dd, "Type2") == 5:
                daten = _ruf(dd, "GetDisplayData")
                linien = [tuple(round(x * 1000, 1) for x in (list(daten.GetLineAtIndex3(i))[4:6] + list(daten.GetLineAtIndex3(i))[7:9]))
                          for i in range(_ruf(daten, "GetLineCount"))]
                ann = [round(x * 1000, 1) for x in list(_ruf(_ruf(dd, "GetAnnotation"), "GetPosition"))[:2]]
                print("Radiusmaß", kurzname(dd), "Zahl", ann, "Linien", linien)
    finally:
        sw.schliesse(app, drw)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
