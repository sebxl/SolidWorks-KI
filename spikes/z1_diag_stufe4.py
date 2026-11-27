"""Spike Z1.3 Stufe 4 (Toleranzen, Ⓔ, Rauheit, Bezug, Form/Lage): Was überlebt Speichern und Wiederöffnen der Zeichnung,
wenn das Teil nie gespeichert wird (SHA-Regel)? Wegwerf-Diagnose.

Setzt in einer gespeicherten Spannplatten-Zeichnung (Hauptansicht „Zeichenansicht1“):
- Passung H7 und Zusatz „ Ⓔ“ an D1@f1_skizze (200), Abmaße +0,1/−0,05 an D2@f1_skizze (120),
- ein Rauheitssymbol „Ra 0,8“ an einer Kreiskante der Stiftbohrung (st) und ein freies Rauheitssymbol,
- ein Bezugsdreieck „A“ an einer geraden Kante von f1, zwei Toleranzrahmen (Ebenheit 0,02; Rechtwinkligkeit 0,02 zu A),
- einen freien Hinweis,
speichert als `<name>_s4.SLDDRW` und PDF, schließt alles ohne Speichern des Teils, öffnet die Kopie neu und liest zurück.
Prüft dazu die Stufe-3-Zusätze (Präfix/Suffix an D3@m1) und die SHA-256 der Teildatei vorher/nachher.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4 <zeichnung.SLDDRW> <teil.SLDPRT>
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
TOL_BILAT, TOL_FIT = 2, 7                    # swTolType_e
EINE_KONFIG = 1                              # swInConfigurationOpts_e.swThisConfiguration
PRAEFIX, SUFFIX = 1, 2                       # swDimensionTextParts_e
SF_BEARBEITET, FUEHRUNG_GERADE, PFEIL_ZU = 1, 1, 1   # swSFSymType_e, swLeaderStyle_e, swArrowStyle_e
KANTE = 1                                    # swViewEntityType_e.swViewEntityType_Edge


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def ansicht(drw, name):
    v = _ruf(drw, "GetFirstView")
    while v is not None and _ruf(v, "GetName2") != name:
        v = _ruf(v, "GetNextView")
    return v


def kante_von(v, merkmal: str, kreis: bool):
    for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
        try:
            namen = {_ruf(_ruf(f, "GetFeature"), "Name") for f in list(_ruf(k, "GetTwoAdjacentFaces2") or ()) if f}
            if merkmal in namen and bool(_ruf(_ruf(k, "GetCurve"), "IsCircle")) == kreis:
                return k
        except Exception:  # noqa: BLE001
            continue
    return None


def masse(v) -> dict:
    aus = {}
    for dd in _anzeige(v):
        dim = dd.GetDimension2(0)
        tol = _ruf(dim, "Tolerance")
        aus[kurzname(dd)] = {"tol_typ": _ruf(tol, "Type"), "passung": _ruf(tol, "GetHoleFitValue"),
                             "praefix": dd.GetText(PRAEFIX), "suffix": dd.GetText(SUFFIX)}
    return aus


def anmerkungen(v) -> dict:
    aus = {"gtol": [], "bezug": [], "rauheit": []}
    g = _ruf(v, "GetFirstGTOL")
    while g is not None:
        aus["gtol"].append({"werte": list(g.GetFrameValues(1) or ()), "symbole": list(g.GetFrameSymbols2(1) or ())})
        g = _ruf(g, "GetNextGTOL")
    d = _ruf(v, "GetFirstDatumTag")
    while d is not None:
        aus["bezug"].append(_ruf(d, "GetLabel"))
        d = _ruf(d, "GetNext")
    s = _ruf(v, "GetFirstSFSymbol")
    while s is not None:
        aus["rauheit"].append([s.GetText(i) for i in range(10)])
        s = _ruf(s, "GetNext")
    return aus


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    sha_vor = sha(teil)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    kopie = pfad.with_name(pfad.stem + "_s4.SLDDRW")
    werte = {}
    v = ansicht(drw, "Zeichenansicht1")
    for dd in _anzeige(v):
        name = kurzname(dd)
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        if name == "D1@f1_skizze":
            tol.Type = TOL_FIT
            werte["fit"] = tol.SetFitValues("H7", "")
            werte["e_suffix"] = dd.SetText(SUFFIX, " Ⓔ")
        elif name == "D2@f1_skizze":
            tol.Type = TOL_BILAT
            werte["bilat"] = tol.SetValues2(-0.00005, 0.0001, EINE_KONFIG, None)
    drw.ClearSelection2(True)
    k = kante_von(v, "st", True) or kante_von(v, "st_fase", True)
    werte["sf_kante"] = k is not None and bool(v.SelectEntity(k, False))
    ext = _ruf(drw, "Extension")
    sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, FUEHRUNG_GERADE, 0.25, 0.20, 0, 0, PFEIL_ZU,
                                        "", "", "", "", "Ra 0,8", "", "")
    werte["sf_an_kante"] = sf is not None
    drw.ClearSelection2(True)
    sf2 = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, 0, 0.33, 0.07, 0, 0, PFEIL_ZU, "", "", "", "", "Ra 3,2", "", "")
    werte["sf_frei"] = sf2 is not None
    drw.ClearSelection2(True)
    g = kante_von(v, "f1", False)
    werte["bezug_kante"] = g is not None and bool(v.SelectEntity(g, False))
    tag = _ruf(drw, "InsertDatumTag2")
    werte["bezug"] = tag is not None and tag.SetLabel("A")
    drw.ClearSelection2(True)
    werte["gtol_kante"] = g is not None and bool(v.SelectEntity(g, False))
    gt = _ruf(drw, "InsertGtol")
    if gt is not None:
        gt.SetFrameSymbols2(1, "<IGTOL-FLAT>", False, "", False, "", "", "", "")
        gt.SetFrameValues2(1, "0,02", "", "", "", "")
    werte["gtol_eben"] = gt is not None
    drw.ClearSelection2(True)
    gt2 = _ruf(drw, "InsertGtol")
    if gt2 is not None:
        gt2.SetFrameSymbols2(1, "<IGTOL-PERP>", False, "", False, "", "", "", "")
        gt2.SetFrameValues2(1, "0,02", "", "A", "", "")
        _ruf(gt2, "GetAnnotation").SetPosition2(0.30, 0.25, 0)
    werte["gtol_senkrecht"] = gt2 is not None
    drw.ClearSelection2(True)
    werte["hinweis"] = drw.InsertNote("Allgemeintoleranzen ISO 2768-1:1989-m\nTolerierung ISO 8015") is not None
    _ruf(drw, "EditRebuild3")
    werte["vor_speichern"] = {"masse": {n: m for n, m in masse(v).items() if n in ("D1@f1_skizze", "D2@f1_skizze", "D3@m1")},
                              **anmerkungen(v)}
    ext.SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    ext.SaveAs(str(kopie.with_suffix(".pdf")), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    app.CloseAllDocuments(True)  # ohne Speichern – das Teil wird nicht gespeichert
    werte["teil_sha_unveraendert_nach_schliessen"] = sha(teil) == sha_vor
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    werte["nach_wiederoeffnen"] = {"masse": {n: m for n, m in masse(v).items() if n in ("D1@f1_skizze", "D2@f1_skizze", "D3@m1")},
                                   **anmerkungen(v)}
    app.CloseAllDocuments(True)
    werte["teil_sha_unveraendert_am_ende"] = sha(teil) == sha_vor
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    import pymupdf
    with pymupdf.open(kopie.with_suffix(".pdf")) as doc:
        text = doc[0].get_text()
    print("PDF enthält:", {t: t in text for t in ("H7", "Ⓔ", "0,8", "3,2", "0,02", "+0,10", "-0,05", "ISO 8015")})


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
