"""Diagnose Z1.3 Stufe 2 (Nutzer 19.11.2026: „Ggf. solltest du die untere Seitenansicht zu einer Schnittansicht
anpassen“): Schnitt aus der Hauptansicht eines Frästeils, Schnittlinie waagrecht durch die Mitte eines Merkmals,
Schnitt unter der Hauptansicht – einmal ohne, einmal mit `swCreateSectionView_ChangeDirection` (4). Speichert je ein
PDF; danach Lage der Taschenkanten in beiden prüfen (Öffnung oben wie in der Projektion darunter?). Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_frässchnitt <zeichnung.SLDDRW> <ansicht> <merkmal> <option>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.zeichnen import SAVE_SILENT, _in_ansicht, _kanten, _ruf, _umriss_mm, _waehle_ansicht

SW_DOC_DRAWING = 3


def main(pfad: Path, ansicht: str, merkmal: str, option: int) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    mu = mathutil(app)
    ziel = pfad.with_name(f"{pfad.stem}_schnitt{option}.pdf")
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        punkte = [p for n, liste in _kanten(mu, v).items() if n == merkmal for a, e, _ in liste for p in (a, e)]
        ym = (min(p[1] for p in punkte) + max(p[1] for p in punkte)) / 2
        x0, y0, x1, y1 = _umriss_mm(v)
        print("Merkmal", merkmal, "Mitte y", round(ym, 1), "Umriss", [round(x, 1) for x in (x0, y0, x1, y1)])
        _waehle_ansicht(drw, v)
        a, b = _in_ansicht(v, (x0 - 5) / 1000, ym / 1000), _in_ansicht(v, (x1 + 5) / 1000, ym / 1000)
        _ruf(drw, "SketchManager").CreateLine(a[0], a[1], 0, b[0], b[1], 0)
        s = drw.CreateSectionViewAt5((x0 + x1) / 2 / 1000, (y0 - 90) / 1000, 0, "B", option, None, 0)
        print("Schnitt", s is not None, _ruf(s, "GetName2") if s else None,
              "Umriss", [round(x, 1) for x in _umriss_mm(s)] if s else None)
        if s is not None:
            je = _kanten(mu, s)
            for n in (merkmal, "f1"):
                pts = [p for a, e, _ in je.get(n, []) for p in (a, e)]
                if pts:
                    print(f"  {n}: x {min(p[0] for p in pts):.1f}–{max(p[0] for p in pts):.1f}, "
                          f"y {min(p[1] for p in pts):.1f}–{max(p[1] for p in pts):.1f}")
        _ruf(drw, "EditRebuild3")
        _ruf(drw, "Extension").SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
        print("gespeichert", ziel.name)
    finally:
        sw.schliesse(app, drw)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]))
