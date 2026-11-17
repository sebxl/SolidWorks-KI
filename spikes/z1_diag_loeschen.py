"""Diagnose Z1.3 Stufe 2: Welcher Weg entfernt ein eingefügtes Modellmaß wirklich aus einer Zeichenansicht?
Zählt die Maße der Ansicht vor/nach jedem Versuch (nicht den Rückgabewert). Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_loeschen <teil.SLDPRT>
"""

import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import callout_leer, verbinde
from swki.zeichnung.bemassen import _anzeige, _einfuegen, kurzname
from swki.zeichnung.zeichnen import SW_DEFAULT_TEMPLATE_DRAWING, _blatt, _ruf


def main(teil: Path) -> None:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    model = oeffne(app, teil)
    drw = app.NewDocument(app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING), 0, 0, 0)
    try:
        _blatt(drw, "A3quer", (1, 2), r.zeichnung["A3quer"])
        v = drw.CreateDrawViewFromModelView3(str(teil), "*Oben", 0.2, 0.15, 0)
        _einfuegen(drw, v, True)
        sm = _ruf(drw, "SelectionManager")

        def zahl():
            return len(_anzeige(v))

        print("nach Einfügen", zahl())
        versuche = [
            ("Select3+EditDelete", lambda dd: (drw.ClearSelection2(True), _ruf(dd, "GetAnnotation").Select3(False, callout_leer()),
                                              print("   ausgewählt", sm.GetSelectedObjectCount2(-1)), drw.EditDelete())),
            ("Select2+DeleteSelection2", lambda dd: (drw.ClearSelection2(True), _ruf(dd, "GetAnnotation").Select2(False, 0),
                                                    print("   ausgewählt", sm.GetSelectedObjectCount2(-1)),
                                                    _ruf(drw, "Extension").DeleteSelection2(0))),
            ("Visible=Hidden", lambda dd: setattr(_ruf(dd, "GetAnnotation"), "Visible", 3)),
        ]
        for name, versuch in versuche:
            dds = _anzeige(v)
            if not dds:
                break
            vorher, ziel = zahl(), kurzname(dds[0])
            versuch(dds[0])
            print(name, ziel, vorher, "→", zahl(), "| noch da:", ziel in [kurzname(d) for d in _anzeige(v)])
    finally:
        sw.schliesse(app, drw)
        sw.schliesse(app, model)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
