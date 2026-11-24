"""Diagnose Z1.3 Stufe 2, Einzelheit: Wie verhalten sich IView.Position, GetOutline und ScaleDecimal einer
Detailansicht beim Umstellen von Maßstab und Lage? Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_einzelheit_lage <zeichnung.SLDDRW>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, r8_array, verbinde
from swki.zeichnung.zeichnen import _ruf, _umriss_mm

SW_DOC_DRAWING = 3


def _zeige(drw, v, was):
    pos = [round(x * 1000, 1) for x in list(_ruf(v, "Position"))[:2]]
    u = [round(x, 1) for x in _umriss_mm(v)]
    print(f"{was:28s} Maßstab {_ruf(v, 'ScaleDecimal')} Position {pos} Umriss {u} "
          f"Mitte {[round((u[0] + u[2]) / 2, 1), round((u[1] + u[3]) / 2, 1)]} Größe {[round(u[2] - u[0], 1), round(u[3] - u[1], 1)]}")


def main(pfad: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    try:
        v = _ruf(drw, "GetFirstView")
        det = None
        while v is not None:
            if "Detail" in str(_ruf(v, "GetName2")):
                det = v
            v = _ruf(v, "GetNextView")
        assert det is not None
        print("Ansicht", _ruf(det, "GetName2"), "Typ", _ruf(det, "Type"))
        _zeige(drw, det, "geladen")
        det.ScaleDecimal = 1.0
        _zeige(drw, det, "Maßstab 1.0")
        _ruf(drw, "EditRebuild3")
        _zeige(drw, det, "nach EditRebuild3")
        _ruf(drw, "ForceRebuild3")(False) if False else drw.ForceRebuild3(False)
        _zeige(drw, det, "nach ForceRebuild3")
        det.Position = r8_array([0.300, 0.150])
        _zeige(drw, det, "Position (300, 150)")
        _ruf(drw, "EditRebuild3")
        _zeige(drw, det, "nach EditRebuild3")
        drw.GraphicsRedraw2()
        _zeige(drw, det, "nach GraphicsRedraw2")
    finally:
        sw.schliesse(app, drw)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
