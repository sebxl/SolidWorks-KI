"""Diagnose Z1.3 Stufe 1: Wo landet eine Skizze, die in der aktiven (gedrehten) Ansicht in Blattkoordinaten gezeichnet
wird? Zeichnet nur das Halbschnitt-Rechteck (ohne Ausbruch) und eine Linie durch die Achse, speichert PDF. Wegwerf.

    .venv\Scripts\python.exe -m spikes.z1_diag_ausbruch <spec.yaml> <ausgabe.pdf>
"""

import sys
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_ordner, laeufe
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.spec.laden import lade_spec
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.ansichten import waehle_ansichten
from swki.zeichnung.layout import anordnen
from swki.zeichnung.zeichnen import (AUTO_MITTELLINIEN, SAVE_SILENT, SW_DEFAULT_TEMPLATE_DRAWING, _blatt, _erzeuge, _ruf,
                                     _setze_lage, _umriss_mm, _waehle_ansicht)


def main(spec_pfad: Path, pdf: Path) -> None:
    spec = lade_spec(spec_pfad)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    teil = lauf_ordner(r, auftrag, laeufe(r, auftrag)[-1]) / f"{dateiname(spec, auftrag, standard)}.sldprt"
    app = verbinde(r.sw_jahr)
    model = oeffne(app, teil)
    drw = app.NewDocument(app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING), 0, 0, 0)
    try:
        ext = _ruf(drw, "Extension")
        for t in AUTO_MITTELLINIEN:
            ext.SetUserPreferenceToggle(t, 0, True)
        _blatt(drw, "A3quer", (1, 1), r.zeichnung["A3quer"])
        views = _erzeuge(drw, teil, waehle_ansichten(spec))
        groessen = {k: ((u[2] - u[0]), (u[3] - u[1])) for k, v in views.items() for u in [_umriss_mm(v)]}
        format_, massstab, plaetze = anordnen(groessen)
        _blatt(drw, format_, massstab, r.zeichnung[format_])
        for p in plaetze:
            _setze_lage(views[p.rolle], p.mitte_mm)
        v = views["haupt"]
        x0, y0, x1, y1 = (c / 1000 for c in _umriss_mm(v))
        ym = (y0 + y1) / 2
        print("Umriss haupt mm", [round(c * 1000, 1) for c in (x0, y0, x1, y1)], "Lage", list(_ruf(v, "Position")),
              "Winkel", _ruf(v, "Angle"))
        _waehle_ansicht(drw, v)
        sm = _ruf(drw, "SketchManager")
        segs = list(sm.CreateCornerRectangle(x0 - 0.003, ym, 0, x1 + 0.003, y1 + 0.003, 0) or ())
        linie = sm.CreateLine(x0 - 0.01, ym, 0, x1 + 0.01, ym, 0)
        print("Rechteck-Segmente", len(segs), "Linie", linie is not None)
        _ruf(drw, "EditRebuild3")
        f, w = byref_long(), byref_long()
        ext.SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), f, w)
    finally:
        sw.schliesse(app, drw)
        sw.schliesse(app, model)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
