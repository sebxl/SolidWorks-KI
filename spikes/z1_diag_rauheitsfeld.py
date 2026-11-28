"""Spike Z1 Rauheitsfeld (Nutzer 28.11.2026): Sammelrauheit als Feld über dem Schriftfeld – Rauheitssymbol nach ISO
1302:2002 (Feld a „Ra 3,2“) ohne Hinweislinie, daneben der Hinweis „Alle Flächen ohne andere Angabe“, Rahmen als
Skizzenrechteck auf dem Blatt. Fragen: Welcher Punkt des Symbols ist `SetPosition2`/`GetPosition`? Wie groß ist es im
PDF (Grundsymbol und „Bearbeitung verlangt“)? Folgt die Blattskizze dem Blattmaßstab (1:2)? Findet `GetFirstSFSymbol`
der Blattansicht das Symbol nach dem Wiederöffnen samt Feld a, und wie sieht seine Anhängung aus?

    .venv\\Scripts\\python.exe -m spikes.z1_diag_rauheitsfeld
"""

import json
import sys

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, verbinde
from swki.zeichnung.zeichnen import (SF_NORM, SF_NORM_1302_2002, SW_DEFAULT_TEMPLATE_DRAWING, TEXT_HINWEIS,
                                     TEXT_RAUHEIT, _blatt, _ruf, _speichern)

SF_GRUND, SF_BEARBEITET, OHNE_FUEHRUNG, PFEIL = 0, 1, 0, 1   # swSFSymType_e, swLeaderStyle_e, swArrowStyle_e
FELD_A = 8                                                   # swSurfaceFinishSymbolText_e.swSFSymbolRoughnessValue1


def setze_symbol(drw, art: int, x: float, y: float) -> dict:
    ext = _ruf(drw, "Extension")
    _ruf(drw, "EditSheet")
    drw.ClearSelection2(True)
    sf = ext.InsertSurfaceFinishSymbol3(art, OHNE_FUEHRUNG, x / 1000, y / 1000, 0, 0, PFEIL, *([""] * 7))
    if sf is None:
        return {"fehler": "InsertSurfaceFinishSymbol3 None"}
    sf.SetText(FELD_A, "Ra 3,2")
    ann = _ruf(sf, "GetAnnotation")
    vorher = [round(v * 1000, 2) for v in list(_ruf(ann, "GetPosition"))[:2]]
    ann.SetPosition2(x / 1000, y / 1000, 0)
    return {"vorher": vorher, "nachher": [round(v * 1000, 2) for v in list(_ruf(ann, "GetPosition"))[:2]],
            "feld_a": sf.GetText(FELD_A)}


def notiz(drw, text: str, x: float, y: float) -> list:
    _ruf(drw, "EditSheet")
    drw.ClearSelection2(True)
    n = drw.InsertNote(text)
    ann = _ruf(n, "GetAnnotation")
    ann.SetPosition2(x / 1000, y / 1000, 0)
    return [round(v * 1000, 2) for v in list(_ruf(ann, "GetPosition"))[:2]]


def main() -> None:
    r = lade_rechner()
    ordner = r.arbeitsordner / "Z1-SPIKE-RAUHEITSFELD"
    ordner.mkdir(exist_ok=True)
    app = verbinde(r.sw_jahr)
    erg = {}
    drw = app.NewDocument(app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING), 0, 0, 0)
    try:
        ext = _ruf(drw, "Extension")
        fmt = ext.GetUserPreferenceTextFormat(TEXT_RAUHEIT, 0)
        fmt.CharHeight = _ruf(ext.GetUserPreferenceTextFormat(TEXT_HINWEIS, 0), "CharHeight")
        ext.SetUserPreferenceTextFormat(TEXT_RAUHEIT, 0, fmt)
        ext.SetUserPreferenceInteger(SF_NORM, 0, SF_NORM_1302_2002)
        _blatt(drw, "A3quer", (1, 2), r.zeichnung.get("A3quer") or next(iter(r.zeichnung.values())))
        erg["grund"] = setze_symbol(drw, SF_GRUND, 340.0, 85.0)
        erg["bearbeitet"] = setze_symbol(drw, SF_BEARBEITET, 300.0, 85.0)
        erg["notiz1"] = notiz(drw, "Alle Flächen ohne andere Angabe", 250.0, 100.0)
        erg["notiz2"] = notiz(drw, "Alle Flächen ohne\nandere Angabe", 355.0, 89.0)
        _ruf(drw, "EditSheet")
        drw.ClearSelection2(True)
        skm = _ruf(drw, "SketchManager")
        segs = skm.CreateCornerRectangle(330 / 1000, 70 / 1000, 0, 400 / 1000, 90 / 1000, 0)
        erg["rechteck"] = len(list(segs or ()))
        drw.ClearSelection2(True)
        _ruf(drw, "EditRebuild3")
        slddrw, pdf = ordner / "rauheitsfeld.SLDDRW", ordner / "rauheitsfeld.pdf"
        _speichern(ext, slddrw)
        _speichern(ext, pdf)
    finally:
        sw.schliesse(app, drw)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(slddrw), 3, 1 | 2, "", f, w)
    try:
        gelesen = []
        v = _ruf(drw, "GetFirstView")
        while v is not None:
            s = _ruf(v, "GetFirstSFSymbol")
            while s is not None:
                ann = _ruf(s, "GetAnnotation")
                gelesen.append({"ansicht": str(_ruf(v, "GetName2")), "feld_a": s.GetText(FELD_A),
                                "lage": [round(c * 1000, 2) for c in list(_ruf(ann, "GetPosition"))[:2]],
                                "typen": list(_ruf(ann, "GetAttachedEntityTypes") or ()),
                                "anhaengungen": len(list(_ruf(ann, "GetAttachedEntities3") or ()))})
                s = _ruf(s, "GetNext")
            v = _ruf(v, "GetNextView")
        erg["gelesen"] = gelesen
    finally:
        sw.schliesse(app, drw)
    import pymupdf
    pt = 72 / 25.4
    with pymupdf.open(pdf) as doc:
        seite = doc[0]
        h = seite.rect.height / pt
        erg["pdf_texte"] = [(z["spans"][0]["text"] if z["spans"] else "",
                             [round(z["bbox"][0] / pt, 2), round(h - z["bbox"][3] / pt, 2),
                              round(z["bbox"][2] / pt, 2), round(h - z["bbox"][1] / pt, 2)])
                            for b in seite.get_text("dict")["blocks"] for z in b.get("lines", [])
                            if z["bbox"][1] / pt > h - 110]
        linien = []
        for d in seite.get_drawings():
            r_ = d["rect"]
            if r_.y0 / pt > h - 110 and r_.x0 / pt > 240 and r_.y1 / pt < h - 60:
                for e in d["items"]:
                    pts = [p for p in e[1:] if hasattr(p, "x")]
                    linien.append((e[0], [(round(p.x / pt, 2), round(h - p.y / pt, 2)) for p in pts]))
        erg["pdf_linien"] = linien
        seite.get_pixmap(dpi=300, clip=pymupdf.Rect(240 * pt, (h - 110) * pt, 410 * pt, (h - 60) * pt)).save(
            ordner / "rauheitsfeld_ausschnitt.png")
    json.dump(erg, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
