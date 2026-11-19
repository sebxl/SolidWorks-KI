"""Diagnose Z1.3 Stufe 2 (Live 19.11.2026: Kennbuchstabe der Einzelheit auf der Mittellinie): In welchem
Koordinatensystem arbeiten `IDetailCircle.GetLabelPosition`/`SetLabelPosition`? Liest die Lage, vergleicht mit dem
Buchstaben im vorhandenen PDF, setzt ihn 10 mm nach links/oben und speichert ein neues PDF. Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_detailbuchstabe <zeichnung.SLDDRW> <ansicht> <buchstabe>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_double, byref_long, callout_leer, verbinde
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

SW_DOC_DRAWING = 3
PT_MM = 25.4 / 72


def _buchstabe(pdf: Path, b: str):
    import pymupdf

    with pymupdf.open(pdf) as doc:
        p = doc[0]
        h = p.rect.height * PT_MM
        for blk in p.get_text("dict")["blocks"]:
            for z in blk.get("lines", []):
                if "".join(s["text"] for s in z["spans"]).strip() == b:
                    x0, y0, x1, y1 = z["bbox"]
                    return round((x0 + x1) / 2 * PT_MM, 1), round(h - (y0 + y1) / 2 * PT_MM, 1)
    return None


def main(pfad: Path, ansicht: str, b: str) -> None:
    print("PDF vorher:", _buchstabe(pfad.with_suffix(".pdf"), b))
    app = verbinde(lade_rechner().sw_jahr)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    ziel = pfad.with_name(pfad.stem + "_buchstabe.pdf")
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        print("Ansicht", _ruf(v, "GetName2"), "Position", [round(x * 1000, 1) for x in list(_ruf(v, "Position"))[:2]],
              "Maßstab", _ruf(v, "ScaleDecimal"))
        kreise = list(_ruf(v, "GetDetailCircles") or ())
        print("Detailkreise", len(kreise))
        for k in kreise:
            x, y = byref_double(), byref_double()
            k.GetLabelPosition(x, y)
            print("  Label", _ruf(k, "GetLabel"), "GetLabelPosition", round(x.value * 1000, 2), round(y.value * 1000, 2))
            k.SetLabelPosition(x.value - 0.010, y.value + 0.010)
            x2, y2 = byref_double(), byref_double()
            k.GetLabelPosition(x2, y2)
            print("  nach Set", round(x2.value * 1000, 2), round(y2.value * 1000, 2))
        _ruf(drw, "EditRebuild3")
        _ruf(drw, "Extension").SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    finally:
        sw.schliesse(app, drw)
    print("PDF nachher:", _buchstabe(ziel, b))


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
