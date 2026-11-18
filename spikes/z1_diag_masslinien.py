"""Diagnose Z1.3 Stufe 2, Lesbarkeit: Welche Linien (Maßlinie, Hilfslinien) und Textlage liefert IDisplayData je Maß
einer gespeicherten Zeichnung? Grundlage für die Reihenanlage linearer Maße. Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_masslinien <zeichnung.SLDDRW>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import _ruf

SW_DOC_DRAWING = 3


def main(pfad: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    try:
        v = _ruf(drw, "GetFirstView")  # Blatt
        v = _ruf(v, "GetNextView")
        while v is not None:
            print("==", _ruf(v, "GetName2"), [round(x * 1000, 1) for x in _ruf(v, "GetOutline")])
            for dd in _anzeige(v):
                ann = _ruf(dd, "GetAnnotation")
                pos = [round(x * 1000, 1) for x in list(_ruf(ann, "GetPosition"))[:2]]
                daten = _ruf(dd, "GetDisplayData")
                n = _ruf(daten, "GetLineCount")
                linien = []
                for i in range(n):
                    d = list(daten.GetLineAtIndex3(i))
                    linien.append(tuple(round(x * 1000, 1) for x in (d[4], d[5], d[7], d[8])))
                txt = [str(daten.GetTextAtIndex(i)) for i in range(_ruf(daten, "GetTextCount"))]
                tpos = [[round(x * 1000, 1) for x in list(daten.GetTextPositionAtIndex(i))[:2]]
                        for i in range(_ruf(daten, "GetTextCount"))]
                print(f"  {kurzname(dd):22s} typ={_ruf(dd, 'Type2')} ann={pos} text={txt} tpos={tpos}")
                for l in linien:
                    print("     linie", l)
            v = _ruf(v, "GetNextView")
    finally:
        sw.schliesse(app, drw)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
