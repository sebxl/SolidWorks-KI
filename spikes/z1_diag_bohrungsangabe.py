"""Spike Z1.3 Stufe 3: Bohrungsangabe als Hinweis (Notiz) mit Hinweislinie an der Kreiskante.
Fragen: Hängt `InsertNote` die Hinweislinie an die ausgewählte Kante? Wie schreibt man Ø? Lage über
`IAnnotation.SetPosition2`? Beschriftung der Einzelheit („EINZELHEIT“ statt „DETAIL“)? Wegwerf.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_bohrungsangabe <Spannplatte.SLDDRW> [ansicht] [unicode|mod]
"""

import math
import sys
from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.zeichnen import KANTE_SICHTBAR, SAVE_SILENT, _ruf

SW_DOC_DRAWING = 3
PT_MM = 25.4 / 72
TOGGLE_PER_STANDARD = 240   # swDetailingDetailViewLabels_PerStandard (Toggle)
INT_NAME = 241              # swDetailingDetailViewLabels_Name (Integer)
NAME_CUSTOM = 3             # swDetailingViewLabelsName_custom
STR_CUSTOM_NAME = 81        # swDetailingDetailViewLabels_CustomName (String)
OPT_KEINE = 0               # swDetailingNoOptionSpecified


def _kreiskante(mu, view, features=("g1", "m1")):
    """Erste sichtbare Kreiskante, deren Nachbarfläche zu einem der Features gehört: (Kante, Mitte mm, Radius mm)."""
    t = _ruf(view, "ModelToViewTransform")
    for k in list(view.GetVisibleEntities2(callout_leer(), KANTE_SICHTBAR) or ()):
        try:
            c = _ruf(k, "GetCurve")
            if not _ruf(c, "IsCircle"):
                continue
            namen = {_ruf(_ruf(fl, "GetFeature"), "Name") for fl in list(_ruf(k, "GetTwoAdjacentFaces2") or ())
                     if fl is not None}
            cx, cy, cz, *_, r = list(_ruf(c, "CircleParams"))
        except Exception:  # noqa: BLE001 – COM
            continue
        if namen & set(features):
            q = mu.CreatePoint(r8_array([cx, cy, cz])).MultiplyTransform(t).ArrayData
            return k, (q[0] * 1000, q[1] * 1000), r * 1000 * _ruf(view, "ScaleDecimal"), sorted(namen)
    return None


def _pdf_auswerten(pdf: Path, mitte, radius):
    import pymupdf

    with pymupdf.open(pdf) as doc:
        p = doc[0]
        h = p.rect.height * PT_MM
        text = p.get_text()
        print("PDF-Text enthält '5 × M6 – 10 tief':", "5 × M6 – 10 tief" in text, "| 'Ø6':", "Ø6" in text,
              "| 'EINZELHEIT':", "EINZELHEIT" in text, "| 'DETAIL':", "DETAIL" in text)
        print("PDF-Text (Zeilen mit M6/Senkung/Ø/EINZELHEIT/DETAIL):",
              [z for z in text.splitlines() if any(s in z for s in ("M6", "Senkung", "Ø", "EINZELHEIT", "DETAIL", "6 ×"))])
        n = 0
        for d in p.get_drawings():
            for it in d["items"]:
                if it[0] != "l":
                    continue
                for pt, anderes in ((it[1], it[2]), (it[2], it[1])):
                    x, y = pt.x * PT_MM, h - pt.y * PT_MM
                    abst = abs(math.dist((x, y), mitte) - radius)
                    if abst <= 0.5 and math.dist((x, y), mitte) < radius + 0.6:
                        a = (anderes.x * PT_MM, h - anderes.y * PT_MM)
                        if math.dist(a, mitte) > radius + 2:
                            n += 1
                            print(f"  Linienende am Kreis (Abstand {abst:.2f} mm): ({x:.1f},{y:.1f}) -> ({a[0]:.1f},{a[1]:.1f})")
        print("Hinweislinien-Kandidaten am Kreis:", n)


def main(pfad: Path, ansicht: str, schreibweise: str) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = sw.mathutil(app)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    ziel = pfad.with_name(pfad.stem + "_angabe.pdf")
    try:
        v = _ruf(drw, "GetFirstView")
        while v is not None and _ruf(v, "GetName2") != ansicht:
            v = _ruf(v, "GetNextView")
        gef = _kreiskante(mu, v)
        if not gef:
            print("keine Kreiskante in g1/m1 gefunden")
            return
        kante, mitte, radius, namen = gef
        print("Kreiskante: Mitte (mm)", [round(x, 2) for x in mitte], "Radius Blatt (mm)", round(radius, 2), "Features", namen)

        ext = _ruf(drw, "Extension")
        _ruf(drw, "ClearSelection2", True)
        ok = v.SelectEntity(kante, False)
        print("SelectEntity:", ok, "| Auswahlzahl:", _ruf(_ruf(drw, "SelectionManager"), "GetSelectedObjectCount2", -1))

        durchm = "Ø" if schreibweise == "unicode" else "<MOD-DIAM>"
        text = f"5 × M6 – 10 tief\nSenkung {durchm}6 × 90°"
        note = drw.InsertNote(text)
        print("InsertNote ->", note is not None)
        _ruf(drw, "ClearSelection2", True)
        if note is None:
            return
        an = _ruf(note, "GetAnnotation")
        print("Hinweislinien:", _ruf(an, "GetLeaderCount"))
        ents = _ruf(an, "GetAttachedEntities3")
        print("angehängte Entitäten:", None if ents is None else len(list(ents)))
        print("Notiztext zurück:", repr(_ruf(note, "GetText")))
        pos0 = [round(x * 1000, 2) for x in list(_ruf(an, "GetPosition"))[:3]]
        print("Position nach Insert (mm):", pos0)
        ziel_xy = (mitte[0] + 20, mitte[1] + 20)
        print("SetPosition2:", an.SetPosition2(ziel_xy[0] / 1000, ziel_xy[1] / 1000, 0))
        print("Position zurück (mm):", [round(x * 1000, 2) for x in list(_ruf(an, "GetPosition"))[:3]], "Soll", ziel_xy)
        print("Hinweislinien nach Setzen:", _ruf(an, "GetLeaderCount"))

        # Einzelheit-Beschriftung
        print("Toggle PerStandard aus:", ext.SetUserPreferenceToggle(TOGGLE_PER_STANDARD, OPT_KEINE, False))
        print("Name = custom:", ext.SetUserPreferenceInteger(INT_NAME, OPT_KEINE, NAME_CUSTOM))
        print("CustomName:", ext.SetUserPreferenceString(STR_CUSTOM_NAME, OPT_KEINE, "EINZELHEIT"))
        _ruf(drw, "EditRebuild3")
        print("SaveAs PDF:", ext.SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long()))
    finally:
        sw.schliesse(app, drw)
    _pdf_auswerten(ziel, mitte, radius)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "Zeichenansicht1",
         sys.argv[3] if len(sys.argv) > 3 else "unicode")
