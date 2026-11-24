"""Diagnose Z1.3 Stufe 2 (Nutzer 18.11.2026: Mittellinien für Maße ab Teilmitte): Legt in einer gespeicherten Zeichnung
eine waagrechte und eine senkrechte Linie durch den Modellursprung der Ansicht an – einmal mit
`ISketchManager.CreateCenterLine` – und speichert als PDF daneben; danach zeigt pymupdf, wie die Linien gezeichnet
sind (Strichmuster `dashes`, Breite). Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_mittellinie <zeichnung.SLDDRW> <ansicht>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.zeichnen import SAVE_SILENT, _in_ansicht, _ruf, _umriss_mm, _waehle_ansicht

SW_DOC_DRAWING = 3


def main(pfad: Path, ansicht: str) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    mu = mathutil(app)
    ziel = pfad.with_name(pfad.stem + "_mittellinie.pdf")
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        q = mu.CreatePoint(r8_array([0.0, 0.0, 0.0])).MultiplyTransform(_ruf(v, "ModelToViewTransform")).ArrayData
        ox, oy = q[0] * 1000, q[1] * 1000
        x0, y0, x1, y1 = _umriss_mm(v)
        print("Ursprung auf dem Blatt", round(ox, 1), round(oy, 1), "Umriss", [round(x, 1) for x in (x0, y0, x1, y1)])
        _waehle_ansicht(drw, v)
        sk = _ruf(drw, "SketchManager")
        for (ax, ay), (bx, by) in (((x0 + 3, oy), (x1 - 3, oy)), ((ox, y0 + 3), (ox, y1 - 3))):
            a, b = _in_ansicht(v, ax / 1000, ay / 1000), _in_ansicht(v, bx / 1000, by / 1000)
            seg = sk.CreateCenterLine(a[0], a[1], 0, b[0], b[1], 0)
            print("CreateCenterLine", seg is not None)
        drw.ClearSelection2(True)
        _ruf(drw, "EditRebuild3")
        ok = _ruf(drw, "Extension").SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
        print("gespeichert", ziel.name, ok)
    finally:
        sw.schliesse(app, drw)
    import pymupdf

    mm = 25.4 / 72
    with pymupdf.open(ziel) as doc:
        page = doc[0]
        h = page.rect.height
        for z in page.get_drawings():
            for it in z["items"]:
                if it[0] != "l":
                    continue
                a, b = it[1], it[2]
                ax, ay, bx, by = a.x * mm, (h - a.y) * mm, b.x * mm, (h - b.y) * mm
                lang = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
                durch = (abs(ay - oy) < 0.3 and abs(by - oy) < 0.3) or (abs(ax - ox) < 0.3 and abs(bx - ox) < 0.3)
                if durch and lang > 0.2:
                    print(f"  Linie ({ax:.1f},{ay:.1f})–({bx:.1f},{by:.1f}) Länge {lang:.1f} dashes={z.get('dashes')} "
                          f"breite={z.get('width')}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
