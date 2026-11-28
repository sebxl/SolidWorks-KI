"""Spike Z1.3 Stufe 4, Teil b: Toleranzen und Textzusätze überleben das Wiederöffnen nicht (Teil a,
`z1_diag_stufe4.py`).

Befund aus Teil a: Toleranzen und Textzusätze an eingefügten Modellmaßen hängen am Maß des Teils. Das Teil wird nie
gespeichert (SHA-Regel), deshalb fehlen sie nach dem Wiederöffnen. Das gilt auch für die Zusätze aus Stufe 3
(„4 × … (= 120)“). Das PDF stimmt, weil es vor dem Schließen entsteht; die SLDDRW stimmt nicht.

Teil b prüft den Ausweichweg. Das Modellmaß wird in ein Zeichnungsmaß umgewandelt: angehängte Entitäten lesen
(IAnnotation.GetAttachedEntities3), in der Ansicht auswählen, AddDimension2 an derselben Stelle, Modellmaß löschen.
Danach Toleranz und Zusatz am Zeichnungsmaß setzen, speichern, schließen, neu öffnen und zurücklesen.

Außerdem: Wo liegen das Rauheitssymbol und der freie Hinweis, und sind sie sichtbar? Im PDF von Teil a fehlten sie.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4b <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import hashlib
import json
import sys
from pathlib import Path

from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
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


def wert_mm(dd) -> float:
    return round(dd.GetDimension2(0).GetSystemValue3(EINE_KONFIG, None)[0] * 1000, 3)


def umwandeln(drw, v, dd) -> tuple[object | None, dict]:
    """Modellmaß → Zeichnungsmaß an denselben Entitäten. Liefert (neues Anzeigemaß, Diagnose)."""
    ann = _ruf(dd, "GetAnnotation")
    ents = list(_ruf(ann, "GetAttachedEntities3") or ())
    typen = list(_ruf(ann, "GetAttachedEntityTypes") or ())
    pos = list(_ruf(ann, "GetPosition"))[:2]
    diag = {"name": kurzname(dd), "wert": wert_mm(dd), "entitaeten": len(ents), "typen": typen, "lage": pos}
    drw.ClearSelection2(True)
    gewaehlt = [bool(v.SelectEntity(e, i > 0)) for i, e in enumerate(ents)]
    diag["gewaehlt"] = gewaehlt
    neu = drw.AddDimension2(pos[0], pos[1], 0)
    diag["neu"] = neu is not None
    if neu is not None:
        diag["neu_wert"] = wert_mm(neu)
        diag["neu_name"] = kurzname(neu)
        drw.ClearSelection2(True)
        ann.Select2(False, 0)
        diag["geloescht"] = bool(_ruf(drw, "Extension").DeleteSelection2(0))
    drw.ClearSelection2(True)
    return neu, diag


def lies(drw, v) -> dict:
    masse = []
    for dd in _anzeige(v):
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        masse.append({"name": kurzname(dd), "wert": wert_mm(dd), "tol_typ": _ruf(tol, "Type"),
                      "passung": _ruf(tol, "GetHoleFitValue"), "praefix": dd.GetText(PRAEFIX), "suffix": dd.GetText(SUFFIX)})
    notizen, n = [], _ruf(v, "GetFirstNote")
    while n is not None:
        notizen.append({"text": _ruf(n, "GetText"), "lage": [round(x * 1000, 1) for x in list(_ruf(_ruf(n, "GetAnnotation"), "GetPosition"))[:2]]})
        n = _ruf(n, "GetNext")
    sf, s = [], _ruf(v, "GetFirstSFSymbol")
    while s is not None:
        a = _ruf(s, "GetAnnotation")
        sf.append({"text": s.GetText(5), "lage": [round(x * 1000, 1) for x in list(_ruf(a, "GetPosition"))[:2]],
                   "sichtbar": _ruf(a, "Visible")})
        s = _ruf(s, "GetNext")
    return {"masse": masse, "notizen": notizen, "rauheit": sf}


def kante_von(v, merkmal: str, kreis: bool):
    for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
        try:
            namen = {_ruf(_ruf(f, "GetFeature"), "Name") for f in list(_ruf(k, "GetTwoAdjacentFaces2") or ()) if f}
            if merkmal in namen and bool(_ruf(_ruf(k, "GetCurve"), "IsCircle")) == kreis:
                return k
        except Exception:  # noqa: BLE001
            continue
    return None


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    sha_teil, sha_zeichnung = sha(teil), sha(pfad)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    ext = _ruf(drw, "Extension")
    kopie = pfad.with_name(pfad.stem + "_s4b.SLDDRW")
    v = ansicht(drw, "Zeichenansicht1")
    werte = {"vorher": lies(drw, v), "umwandeln": []}
    ziel = {"D1@f1_skizze": ("fit", None), "D2@f1_skizze": ("bilat", None), "D3@m1": ("zusatz", None)}
    for dd in list(_anzeige(v)):
        name = kurzname(dd)
        if name not in ziel:
            continue
        neu, diag = umwandeln(drw, v, dd)
        werte["umwandeln"].append(diag)
        if neu is None:
            continue
        tol = _ruf(neu.GetDimension2(0), "Tolerance")
        art = ziel[name][0]
        if art == "fit":
            tol.Type = TOL_FIT
            diag["fit"] = tol.SetFitValues("H7", "")
            diag["suffix"] = neu.SetText(SUFFIX, " Ⓔ")
        elif art == "bilat":
            tol.Type = TOL_BILAT
            diag["bilat"] = tol.SetValues2(-0.00005, 0.0001, EINE_KONFIG, None)
        else:
            diag["praefix"] = neu.SetText(PRAEFIX, "4 × ")
            diag["suffix"] = neu.SetText(SUFFIX, " (= 120)")
    k = kante_von(v, "st", True) or kante_von(v, "st_fase", True)
    drw.ClearSelection2(True)
    werte["sf_kante"] = k is not None and bool(v.SelectEntity(k, False))
    sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, FUEHRUNG_GERADE, 0.12, 0.10, 0, 0, PFEIL_ZU,
                                        "", "", "", "", "Ra 0,8", "", "")
    werte["sf"] = sf is not None
    if sf is not None:
        a = _ruf(sf, "GetAnnotation")
        werte["sf_lage_vor"] = [round(x * 1000, 1) for x in list(_ruf(a, "GetPosition"))[:2]]
        werte["sf_setze"] = a.SetPosition2(0.12, 0.10, 0)
    drw.ClearSelection2(True)
    n = drw.InsertNote("Allgemeintoleranzen ISO 2768-1:1989 – m\nTolerierung ISO 8015:2011")
    werte["notiz"] = n is not None
    if n is not None:
        a = _ruf(n, "GetAnnotation")
        werte["notiz_lage_vor"] = [round(x * 1000, 1) for x in list(_ruf(a, "GetPosition"))[:2]]
        werte["notiz_setze"] = a.SetPosition2(0.25, 0.07, 0)
    _ruf(drw, "EditRebuild3")
    werte["nach_setzen"] = lies(drw, v)
    ext.SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    ext.SaveAs(str(kopie.with_suffix(".pdf")), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    werte["original_sha_gleich"] = sha(pfad) == sha_zeichnung
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    werte["nach_wiederoeffnen"] = lies(drw, v)
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich_am_ende"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    import pymupdf
    with pymupdf.open(kopie.with_suffix(".pdf")) as doc:
        text = doc[0].get_text()
    print("PDF enthält:", {t: t in text for t in ("H7", "Ⓔ", "Ra 0,8", "0,8", "4 × 30,00 (= 120)", "+0,10", "-0,05",
                                                    "ISO 8015", "200,00")})


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
