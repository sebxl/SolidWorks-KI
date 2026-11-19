"""Spike Z1.3 Stufe 3 (Task 4): Wo setzt die Hinweislinie einer Bohrungsangabe am Kreis an?
Live 19.11.: nach `IView.SelectEntity(kante)` endet der Pfeil auf der Gegenseite des Kreises (unten links), die
Hinweislinie läuft quer durch die Bohrung. Frage: Hängt `InsertNote` nach `IModelDocExtension.SelectByID2("", "EDGE",
x, y, …)` mit einem Blattpunkt auf dem Kreis den Pfeil an diesen Punkt? Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_hinweis_ansatz <Zeichnung.SLDDRW> <Ansicht> <Feature,…> [winkel_grad]
"""

import math
import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.zeichnen import SAVE_SILENT, _kreiskanten, _ruf

SW_DOC_DRAWING = 3
PT_MM = 25.4 / 72


def main(pfad: Path, ansicht: str, features: set[str], winkel: float) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = sw.mathutil(app)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    ziel = pfad.with_name(pfad.stem + "_ansatz.pdf")
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        kreise = _kreiskanten(mu, v, features)
        print("Kreiskanten:", [(tuple(round(c, 2) for c in m), round(r, 2)) for _, m, r in kreise])
        kante, (mx, my), r = kreise[0]
        px, py = mx + r * math.cos(math.radians(winkel)), my + r * math.sin(math.radians(winkel))
        ext = _ruf(drw, "Extension")
        drw.ClearSelection2(True)
        ok = ext.SelectByID2("", "EDGE", px / 1000, py / 1000, 0, False, 0, callout_leer(), 0)
        sm = _ruf(drw, "SelectionManager")
        n = sm.GetSelectedObjectCount2(-1)
        print("Auswahltypen:", [sm.GetSelectedObjectType3(i, -1) for i in range(1, n + 1)])
        sel = sm.GetSelectedObject6(1, -1) if n else None
        kreis_ok = False
        if sel is not None:
            try:
                c = _ruf(sel, "GetCurve")
                kreis_ok = bool(_ruf(c, "IsCircle"))
                print("gewählt: Kreis", kreis_ok, "Radius Modell-mm", round(list(_ruf(c, "CircleParams"))[6] * 1000, 3))
            except Exception as e:  # noqa: BLE001
                print("gewählt: kein Kantenobjekt", e)
        print(f"SelectByID2 EDGE bei ({px:.2f}, {py:.2f}) mm:", ok, "| Auswahlzahl", n)
        note = drw.InsertNote("4 × Ø6 – durch\nTK Ø40")
        drw.ClearSelection2(True)
        an = _ruf(note, "GetAnnotation")
        print("Hinweislinien:", _ruf(an, "GetLeaderCount"))
        lage = (mx + 25 * math.cos(math.radians(winkel)), my + 25 * math.sin(math.radians(winkel)))
        an.SetPosition2(lage[0] / 1000, lage[1] / 1000, 0)
        _ruf(drw, "EditRebuild3")
        print("SaveAs PDF:", ext.SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long()))
    finally:
        sw.schliesse(app, drw)
    import pymupdf

    with pymupdf.open(ziel) as doc:
        p = doc[0]
        h = p.rect.height * PT_MM
        for d in p.get_drawings():
            for it in d["items"]:
                if it[0] != "l":
                    continue
                for a, b in ((it[1], it[2]), (it[2], it[1])):
                    a, b = (a.x * PT_MM, h - a.y * PT_MM), (b.x * PT_MM, h - b.y * PT_MM)
                    if abs(math.dist(a, (mx, my)) - r) < 0.4 and math.dist(b, (mx, my)) > r + 3:
                        wa = math.degrees(math.atan2(a[1] - my, a[0] - mx))
                        print(f"  Linie vom Kreis ({a[0]:.1f}, {a[1]:.1f}) bei {wa:.0f}° nach ({b[0]:.1f}, {b[1]:.1f})")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], set(sys.argv[3].split(",")), float(sys.argv[4]) if len(sys.argv) > 4 else 45)
