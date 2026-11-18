"""Diagnose Z1.3 Stufe 2, Detailansicht (Nutzer 18.11.2026: dichte Hauptansicht → Einzelheit): Legt in einer
gespeicherten Zeichnung eine Einzelheit um einen Kreis der Elternansicht an, fügt die Modellmaße dort ein und listet
sie; speichert als <name>_einzelheit.SLDDRW/PDF daneben. Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_einzelheit <zeichnung.SLDDRW> <ansicht> <xm> <ym> <r> <x> <y> <n> <d>

Mitte/Radius des Kreises und Lage der Einzelheit in Blatt-mm, Maßstab n:d.
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.bemassen import _anzeige, _einfuegen, kurzname
from swki.zeichnung.zeichnen import SAVE_SILENT, _in_ansicht, _ruf, _umriss_mm, _waehle_ansicht

SW_DOC_DRAWING = 3


def main(pfad: Path, ansicht: str, xm: float, ym: float, r: float, x: float, y: float, n: int, d: int) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        assert v is not None, ansicht
        _waehle_ansicht(drw, v)
        if r > 0:  # Kreis um (xm, ym)
            mx, my = _in_ansicht(v, xm / 1000, ym / 1000)
            px, py = _in_ansicht(v, (xm + r) / 1000, ym / 1000)
            print("Kreis", _ruf(drw, "SketchManager").CreateCircle(mx, my, 0, px, py, 0) is not None)
            art = 1  # swDetCircleCIRCLE
        else:  # Rechteck: (xm, ym) Ecke links unten, Breite/Höhe = -r × (2, 1) – nur für den Spike
            ax, ay = _in_ansicht(v, xm / 1000, ym / 1000)
            bx, by = _in_ansicht(v, (xm - 2 * r) / 1000, (ym - r) / 1000)
            segs = list(_ruf(drw, "SketchManager").CreateCornerRectangle(ax, ay, 0, bx, by, 0) or ())
            sm = _ruf(drw, "SelectionManager")
            print("Rechteck", len(segs), "ausgewählt nach dem Anlegen:", sm.GetSelectedObjectCount2(-1))
            if sm.GetSelectedObjectCount2(-1) < len(segs):
                drw.ClearSelection2(True)
                print("  Select4", [s.Select4(True, callout_leer()) for s in segs], sm.GetSelectedObjectCount2(-1))
            art = 0  # swDetCirclePROFILE
        det = drw.CreateDetailViewAt4(x / 1000, y / 1000, 0, 0, n, d, "B", art, True, False, False, 5)
        print("Einzelheit", det is not None)
        if det is None:
            return
        print("Name", _ruf(det, "GetName2"), "Maßstab", _ruf(det, "ScaleDecimal"), "Umriss", _umriss_mm(det))
        vorher = {kurzname(dd) for dd in _anzeige(v)}
        _einfuegen(drw, det, False)
        neu = [kurzname(dd) for dd in _anzeige(det)]
        print("Maße in der Einzelheit:", len(neu), sorted(neu))
        print("davon schon in der Elternansicht:", sorted(set(neu) & vorher))
        ext = _ruf(drw, "Extension")
        for ziel in (pfad.with_name(pfad.stem + "_einzelheit.SLDDRW"), pfad.with_name(pfad.stem + "_einzelheit.pdf")):
            ok = ext.SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
            print("gespeichert", ziel.name, ok)
    finally:
        sw.schliesse(app, drw)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]), a[1], *(float(z) for z in a[2:7]), int(a[7]), int(a[8]))
