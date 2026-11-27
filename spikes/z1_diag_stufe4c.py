"""Spike Z1.3 Stufe 4, Teil c, Prämissentest: Bleiben Toleranz und Textzusatz an einem Zeichnungsmaß
(AddDimension2 über zwei sichtbare Kanten, wie `bemassen.setze_neu`) beim Speichern und Wiederöffnen erhalten?

Drei getrennte Maße, damit sich ein Fehlschlag zuordnen lässt:
- A: 200 (äußere senkrechte Kanten von f1), nur Passung H7.
- B: 120 (äußere waagrechte Kanten), nur Abmaße +0,1/−0,05.
- C: 200 (dieselben Kanten wie A, tiefer gesetzt), nur Präfix „4 × “ und Suffix „ (= 120) Ⓔ“.

Dazu ein Rauheitssymbol an einer Kreiskante mit einem Marker in jedem der sieben Textparameter (M1…M7). So wird
sichtbar, welcher Platz im PDF als Text erscheint.

Ausgabe: Rückgabewerte, Lesung vor und nach dem Wiederöffnen, PDF-Text und Ausschnitte (PNG) zur Durchsicht.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4c <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import hashlib
import json
import sys
from pathlib import Path

from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

SW_DOC_DRAWING = 3
TOL_BILAT, TOL_FIT = 2, 7
EINE_KONFIG = 1
PRAEFIX, SUFFIX = 1, 2
SF_BEARBEITET, FUEHRUNG_GERADE, PFEIL_ZU = 1, 1, 1
KANTE = 1


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def ansicht(drw, name):
    v = _ruf(drw, "GetFirstView")
    while v is not None and _ruf(v, "GetName2") != name:
        v = _ruf(v, "GetNextView")
    return v


def gerade_kanten(mu, v, merkmal: str) -> list[tuple]:
    """(Kante, Anfang, Ende) in Blatt-mm für gerade sichtbare Kanten, die an `merkmal` grenzen."""
    t = _ruf(v, "ModelToViewTransform")

    def blatt(p):
        q = mu.CreatePoint(r8_array(list(p))).MultiplyTransform(t).ArrayData
        return round(q[0] * 1000, 2), round(q[1] * 1000, 2)

    aus = []
    for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
        try:
            if not _ruf(_ruf(k, "GetCurve"), "IsLine"):
                continue
            namen = {_ruf(_ruf(f, "GetFeature"), "Name") for f in list(_ruf(k, "GetTwoAdjacentFaces2") or ()) if f}
            if merkmal not in namen:
                continue
            cp = _ruf(k, "GetCurveParams3")
            aus.append((k, blatt(_ruf(cp, "StartPoint")), blatt(_ruf(cp, "EndPoint"))))
        except Exception:  # noqa: BLE001
            continue
    return aus


def kreiskante(v, merkmal: str):
    for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
        try:
            namen = {_ruf(_ruf(f, "GetFeature"), "Name") for f in list(_ruf(k, "GetTwoAdjacentFaces2") or ()) if f}
            if merkmal in namen and _ruf(_ruf(k, "GetCurve"), "IsCircle"):
                return k
        except Exception:  # noqa: BLE001
            continue
    return None


def wert_mm(dd) -> float | None:
    """Modellmaße: GetSystemValue3; Zeichnungsmaße liefern dort None (Live 27.11.) → GetSystemValue2("")."""
    dim = dd.GetDimension2(0)
    w = dim.GetSystemValue3(EINE_KONFIG, None)
    if w is not None:
        return round(w[0] * 1000, 3)
    w = dim.GetSystemValue2("")
    return None if w is None else round(w * 1000, 3)


def lies(v, namen: set[str]) -> dict:
    aus = {}
    for dd in _anzeige(v):
        n = kurzname(dd)
        if n not in namen:
            continue
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        aus[n] = {"wert": wert_mm(dd), "tol_typ": _ruf(tol, "Type"), "passung": _ruf(tol, "GetHoleFitValue"),
                  "praefix": dd.GetText(PRAEFIX), "suffix": dd.GetText(SUFFIX)}
    sf, s = [], _ruf(v, "GetFirstSFSymbol")
    while s is not None:
        sf.append([s.GetText(i) for i in range(10)])
        s = _ruf(s, "GetNext")
    aus["rauheit"] = sf
    return aus


def masse_setzen(drw, v, kanten: list, lage_m: tuple[float, float]):
    drw.ClearSelection2(True)
    ok = [bool(v.SelectEntity(kanten[0], False)), bool(v.SelectEntity(kanten[1], True))]
    dd = drw.AddDimension2(lage_m[0], lage_m[1], 0)
    drw.ClearSelection2(True)
    return dd, ok


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    sha_teil, sha_zeichnung = sha(teil), sha(pfad)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    ext = _ruf(drw, "Extension")
    kopie = pfad.with_name(pfad.stem + "_s4c.SLDDRW")
    v = ansicht(drw, "Zeichenansicht1")
    k = gerade_kanten(mu, v, "f1")
    senk = [x for x in k if abs(x[1][0] - x[2][0]) < 0.05]
    waag = [x for x in k if abs(x[1][1] - x[2][1]) < 0.05]
    links, rechts = min(senk, key=lambda x: x[1][0]), max(senk, key=lambda x: x[1][0])
    unten, oben = min(waag, key=lambda x: x[1][1]), max(waag, key=lambda x: x[1][1])
    werte = {"kanten": {"links": links[1:], "rechts": rechts[1:], "unten": unten[1:], "oben": oben[1:]}}
    mitte_x = (links[1][0] + rechts[1][0]) / 2000
    a, werte["a_gewaehlt"] = masse_setzen(drw, v, [links[0], rechts[0]], (mitte_x, oben[1][1] / 1000 + 0.045))
    b, werte["b_gewaehlt"] = masse_setzen(drw, v, [unten[0], oben[0]], (rechts[1][0] / 1000 + 0.04, (unten[1][1] + oben[1][1]) / 2000))
    c, werte["c_gewaehlt"] = masse_setzen(drw, v, [links[0], rechts[0]], (mitte_x, oben[1][1] / 1000 + 0.06))
    namen = set()
    for schluessel, dd in (("a", a), ("b", b), ("c", c)):
        werte[schluessel] = None if dd is None else {"name": kurzname(dd), "wert": wert_mm(dd)}
        if dd is not None:
            namen.add(kurzname(dd))
    if a is not None:
        tol = _ruf(a.GetDimension2(0), "Tolerance")
        tol.Type = TOL_FIT
        werte["a_fit"] = tol.SetFitValues("H7", "")
    if b is not None:
        tol = _ruf(b.GetDimension2(0), "Tolerance")
        tol.Type = TOL_BILAT
        werte["b_bilat"] = tol.SetValues2(-0.00005, 0.0001, EINE_KONFIG, None)
    if c is not None:
        werte["c_praefix"] = c.SetText(PRAEFIX, "4 × ")
        werte["c_suffix"] = c.SetText(SUFFIX, " (= 120) Ⓔ")
    kk = kreiskante(v, "st") or kreiskante(v, "st_fase")
    drw.ClearSelection2(True)
    werte["sf_kante"] = kk is not None and bool(v.SelectEntity(kk, False))
    sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, FUEHRUNG_GERADE, 0.30, 0.12, 0, 0, PFEIL_ZU,
                                        "M1", "M2", "M3", "M4", "M5", "M6", "M7")
    werte["sf"] = sf is not None
    if sf is not None:
        _ruf(sf, "GetAnnotation").SetPosition2(0.30, 0.12, 0)
    drw.ClearSelection2(True)
    _ruf(drw, "EditRebuild3")
    werte["vor_speichern"] = lies(v, namen)
    ext.SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    pdf_vor = kopie.with_name(kopie.stem + "_vor.pdf")
    ext.SaveAs(str(pdf_vor), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    werte["original_sha_gleich"] = sha(pfad) == sha_zeichnung
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    werte["nach_wiederoeffnen"] = lies(v, namen)
    pdf_nach = kopie.with_name(kopie.stem + "_nach.pdf")
    _ruf(drw, "Extension").SaveAs(str(pdf_nach), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich_am_ende"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    import pymupdf
    for pdf in (pdf_vor, pdf_nach):
        with pymupdf.open(pdf) as doc:
            text = doc[0].get_text()
            doc[0].get_pixmap(dpi=110).save(str(pdf.with_suffix(".png")))
        print(pdf.name, {t: t in text for t in ("H7", "Ⓔ", "+0,10", "-0,05", "−0,05", "4 × 200,00", "(= 120)",
                                                  "M1", "M2", "M3", "M4", "M5", "M6", "M7")})


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
