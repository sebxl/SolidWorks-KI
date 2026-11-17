"""Spike Z1.0 Zeichnungsableitung (Plan 2026-11-16, Task 1): Was trägt die SolidWorks-API ohne Dialog? Wegwerf, kein
Produktionscode. Aufruf aus dem Repo-Wurzelordner (Worktree), SolidWorks frisch gestartet, Teile gebaut:

    .venv\\Scripts\\python.exe -m spikes.z1_zeichnung <buchse.SLDPRT> <spannplatte.SLDPRT> <ausgabeordner>

Jede Frage schreibt ihr Ergebnis sofort nach <ausgabeordner>/spike-z1.json (hängt ein Aufruf an einem Dialog, zeigt die
letzte Zeile, wo). API-Aufrufe nachgeschlagen mit `swki api methode|enum` (Liste in docs/zeichnungsableitung/spike-z1.md).
"""

import hashlib
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

import win32com.client
import win32com.client.dynamic

from spikes.s9a_gemeinsam import start
from spikes.s9b_gemeinsam import byref_long
from swki.verbindung import callout_leer

# Enums laut swki api enum
SW_DOC_PART, SW_DOC_DRAWING = 1, 3
SW_OPEN_SILENT = 1
SW_DEFAULT_TEMPLATE_DRAWING = 10  # swUserPreferenceStringValue_e
INS_DIMS, INS_MARKED, INS_NOT_MARKED, INS_HOLE_CALLOUT = 8, 32768, 524288, 1048576  # swInsertAnnotation_e
VIEW_EDGE = 1  # swViewEntityType_e
TOL_FIT = 7  # swTolType_e.swTolFIT
TEXT_SUFFIX = 2  # swDimensionTextParts_e
SF_STANDARD = 629  # swDetailingSFSymbolStandard
SF_21920 = 2  # swDetailingSFSymbolStandard_e
SF_MACHINING_REQ = 1  # swSFSymType_e
LEADER_STRAIGHT, ARROW_CLOSED = 1, 1
SAVE_SILENT = 1

ergebnis: dict = {}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ruf(obj, name, *args):
    """Methode aufrufen; nullargumentige Member liefert der dynamische Dispatch teils schon beim Zugriff (swki.verbindung)."""
    x = getattr(obj, name)
    if args:
        return x(*args)
    return x if isinstance(x, win32com.client.dynamic.CDispatch) or not callable(x) else x()


def merke(frage: str, **werte) -> None:
    ergebnis[frage] = werte
    AUS.write_text(json.dumps(ergebnis, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(frage, json.dumps(werte, ensure_ascii=False, default=str)[:400], flush=True)


def frage(name):
    def deko(fn):
        def lauf(*a, **k):
            t0 = time.time()
            merke(name, status="läuft")
            try:
                werte = fn(*a, **k) or {}
                merke(name, status="ok", dauer_s=round(time.time() - t0, 2), **werte)
            except Exception as e:  # Spike: jede Frage für sich
                merke(name, status="fehler", fehler=repr(e), trace=traceback.format_exc()[-1500:])
        return lauf
    return deko


def oeffne(app, pfad: Path, art: int):
    fehler, warn = byref_long(), byref_long()
    doc = app.OpenDoc6(str(pfad), art, SW_OPEN_SILENT, "", fehler, warn)
    if doc is None:
        raise RuntimeError(f"OpenDoc6 {pfad.name}: Fehler {fehler.value}")
    return doc


def views(drw) -> list:
    sheet = ruf(drw, "GetCurrentSheet")
    return [v for v in (ruf(sheet, "GetViews") or ())]


def anzeige_masse(view) -> list:
    dd, aus = ruf(view, "GetFirstDisplayDimension5"), []
    while dd is not None:
        aus.append(dd)
        dd = ruf(dd, "GetNext5")
    return aus


def mass_info(dd) -> dict:
    dim = dd.GetDimension2(0)
    tol = ruf(dim, "Tolerance")
    ann = ruf(dd, "GetAnnotation")
    ents = ruf(ann, "GetAttachedEntities3") or ()
    return {"name": ruf(dim, "FullName"), "wert_mm": round(ruf(dim, "SystemValue") * 1000, 4),
            "tol_typ": ruf(tol, "Type"), "passung": ruf(tol, "GetHoleFitValue"),
            "text_suffix": dd.GetText(TEXT_SUFFIX), "klammer": ruf(dd, "ShowParenthesis"),
            "pruefmass": ruf(dd, "Inspection"), "kanten": len(ents), "lage_m": list(ruf(ann, "GetPosition") or ())}


def main(buchse: Path, platte: Path, ordner: Path) -> None:
    r, app = start()
    ordner.mkdir(parents=True, exist_ok=True)

    @frage("1_service_pack")
    def q1():
        rev = ruf(app, "RevisionNumber")
        return {"revision": rev, 
                "hinweis": "Methodenverfügbarkeit SP-abhängig: unten in q8 an einer Ansicht probiert"}
    q1()

    vorlage = app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING)
    sha_buchse_vorher = sha(buchse)
    zust: dict = {}

    def neue_zeichnung(teilpfad: Path) -> tuple:
        """Teil öffnen (Create1stAngleViews2 lieferte mit nur gespeichertem Teil False), Zeichnung anlegen, Blatt auf A3
        quer, 1:1, Projektionsmethode 1, dann Standardansichten; sonst Erstansicht über CreateDrawViewFromModelView3."""
        teil = oeffne(app, teilpfad, SW_DOC_PART)
        ansichtsnamen = list(ruf(teil, "GetModelViewNames") or ())
        drw = app.NewDocument(vorlage, 0, 0, 0)
        if drw is None:
            raise RuntimeError(f"NewDocument({vorlage}) lieferte None")
        sheet = ruf(drw, "GetCurrentSheet")
        vorher = list(ruf(sheet, "GetProperties2") or ())
        gesetzt = sheet.SetProperties2(8, 13, 1, 1, True, 0.42, 0.297, True)  # A3, keine Vorlage, 1:1, 1. Winkel
        nachher = list(ruf(sheet, "GetProperties2") or ())
        ok = drw.Create1stAngleViews2(str(teilpfad))
        ersatz = None
        if not views(drw):
            vorne = next((n for n in ansichtsnamen if "vorn" in n.lower() or "front" in n.lower()), ansichtsnamen[0])
            ersatz = vorne
            drw.CreateDrawViewFromModelView3(str(teilpfad), vorne, 0.12, 0.17, 0)
        return drw, {"blatt_vorher": vorher, "SetProperties2": gesetzt, "blatt_nachher": nachher,
                     "Create1stAngleViews2": ok, "modellansichten": ansichtsnamen, "ersatz_ansicht": ersatz}

    def masse_einfuegen(drw, typen: int) -> dict:
        """Laut Hilfe-Beispiel Insert_Model_Annotations: Ansicht als DRAWINGVIEW wählen, aktivieren, Auswahl leeren,
        dann InsertModelAnnotations4 (n=8, seit 2024) für alle Ansichten. HiddenFeatureDims=True ist nötig, weil swki die
        Skizzen ausblendet (Diagnose spikes/z1_diag_modellmasse.py: sonst 0 bzw. 1 Maß)."""
        ext = ruf(drw, "Extension")
        name = ruf(views(drw)[0], "GetName2")
        ext.SelectByID2(name, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
        drw.ActivateView(name)
        drw.ClearSelection2(True)
        t0 = time.time()
        anns = drw.InsertModelAnnotations4(0, typen, True, False, True, False, False, False)
        return {"annotationen": len(anns or ()), "s": round(time.time() - t0, 2)}

    @frage("2_zeichnung_und_ansichten")
    def q2():
        drw, info = neue_zeichnung(buchse)
        zust["drw"] = drw
        vs = views(drw)
        return {"vorlage": vorlage, **info,
                "ansichten": [{"name": ruf(v, "GetName2"), "lage": list(ruf(v, "Position") or ()),
                               "umriss": list(ruf(v, "GetOutline") or ())} for v in vs]}
    q2()

    @frage("3_schnitt_und_einzelheit")
    def q3():
        drw = zust["drw"]
        vs = views(drw)
        v = vs[0]
        name = ruf(v, "GetName2")
        x0, y0, x1, y1 = list(ruf(v, "GetOutline"))
        xm = (x0 + x1) / 2
        drw.ActivateView(name)
        sm = ruf(drw, "SketchManager")
        linie = sm.CreateLine(xm, y0 - 0.01, 0, xm, y1 + 0.01, 0)
        schnitt = drw.CreateSectionViewAt5(x1 + 0.08, (y0 + y1) / 2, 0, "A", 0, None, 0)
        werte = {"ansicht": name, "linie": linie is not None, "schnitt": schnitt is not None}
        if schnitt is not None:
            werte["schnitt_name"] = ruf(schnitt, "GetName2")
        drw.ActivateView(name)
        kreis = sm.CreateCircleByRadius(x1 - 0.005, y0 + 0.005, 0, 0.006)
        detail = drw.CreateDetailViewAt4(x1 + 0.08, y0 - 0.05, 0, 0, 2.0, 1.0, "Z", 1, True, False, False, 5)
        werte |= {"kreis": kreis is not None, "einzelheit": detail is not None}
        if detail is not None:
            werte["einzelheit_name"] = ruf(detail, "GetName2")
        return werte
    q3()

    @frage("4_modellmasse_einfuegen")
    def q4():
        drw = zust["drw"]
        werte = {}
        for typen, schluessel in ((INS_MARKED, "markiert"), (INS_HOLE_CALLOUT, "bohrungsangabe")):
            vorher = sum(len(anzeige_masse(v)) for v in views(drw))
            t0 = time.time()
            je_ansicht = masse_einfuegen(drw, typen)
            nachher = sum(len(anzeige_masse(v)) for v in views(drw))
            werte[schluessel] = {"je_ansicht": je_ansicht, "masse_neu": nachher - vorher, "s": round(time.time() - t0, 2)}
        werte["masse_je_ansicht"] = {ruf(v, "GetName2"): [mass_info(d)["name"] + " = " + str(mass_info(d)["wert_mm"])
                                                          for d in anzeige_masse(v)] for v in views(drw)}
        namen = [mass_info(d)["name"] for v in views(drw) for d in anzeige_masse(v)]
        werte["doppelt"] = sorted({n for n in namen if namen.count(n) > 1})
        return werte
    q4()

    @frage("5_markierung_und_teildatei")
    def q5():
        # a) Teil-Kopie: MarkedForDrawing an einem Maß ändern und speichern -> SHA ändert sich?
        kopie = ordner / "buchse_kopie.SLDPRT"
        shutil.copy2(buchse, kopie)
        sha_kopie = sha(kopie)
        teil = oeffne(app, kopie, SW_DOC_PART)
        feat, markiert, gesamt, geaendert = ruf(teil, "FirstFeature"), 0, 0, None
        while feat is not None:
            dd = ruf(feat, "GetFirstDisplayDimension")
            while dd is not None:
                gesamt += 1
                if ruf(dd, "MarkedForDrawing"):
                    markiert += 1
                    if geaendert is None:
                        dd.MarkedForDrawing = False
                        geaendert = ruf(dd.GetDimension2(0), "FullName")
                dd = feat.GetNextDisplayDimension(dd)
            feat = ruf(feat, "GetNextFeature")
        fehler, warn = byref_long(), byref_long()
        teil.Save3(SAVE_SILENT, fehler, warn)
        app.CloseDoc(ruf(teil, "GetTitle"))
        # b) Zeichnung: ein eingefügtes Maß löschen, Zeichnung speichern -> Teildatei unverändert?
        drw = zust["drw"]
        geloescht = None
        for v in views(drw):
            ds = anzeige_masse(v)
            if ds:
                ann = ruf(ds[0], "GetAnnotation")
                drw.ClearSelection2(True)
                ann.Select3(False, callout_leer())
                geloescht = ruf(ds[0].GetDimension2(0), "FullName")
                drw.EditDelete()
                break
        return {"teilmasse_gesamt": gesamt, "davon_markiert": markiert, "markierung_entfernt": geaendert,
                "sha_kopie_geaendert": sha(kopie) != sha_kopie, "in_zeichnung_geloescht": geloescht}
    q5()

    @frage("6_mass_neu_setzen")
    def q6():
        drw = zust["drw"]
        v = views(drw)[0]
        kanten = list(v.GetVisibleEntities2(callout_leer(), VIEW_EDGE) or ())
        kreise = []
        for k in kanten:
            c = ruf(k, "GetCurve")
            if ruf(c, "IsCircle"):
                p = list(ruf(c, "CircleParams"))  # cx, cy, cz, ax, ay, az, r
                kreise.append((round(p[1] * 1000, 3), round(p[6] * 1000, 3), k))
        kreise.sort(key=lambda e: (e[0], -e[1]))
        werte = {"sichtbare_kanten": len(kanten), "kreise_y_r_mm": [e[:2] for e in kreise][:12]}
        unten = [e for e in kreise if abs(e[0]) < 1e-3]
        oben = [e for e in kreise if abs(e[0] - 60) < 1e-3]
        if unten and oben:
            drw.ClearSelection2(True)
            werte["sel1"] = v.SelectEntity(unten[0][2], False)
            werte["sel2"] = v.SelectEntity(oben[0][2], True)
            x0, y0, x1, y1 = list(ruf(v, "GetOutline"))
            dim = drw.AddDimension2(x0 - 0.02, (y0 + y1) / 2, 0)
            werte["neues_mass"] = None if dim is None else mass_info(dim)
        return werte
    q6()

    @frage("7_passung_huelle_oberflaeche")
    def q7():
        drw = zust["drw"]
        werte = {}
        ziel = None
        for v in views(drw):
            for d in anzeige_masse(v):
                if abs(ruf(d.GetDimension2(0), "SystemValue") * 1000 - 20) < 1e-6:  # Ø 20 innen
                    ziel = d
                    break
            if ziel:
                break
        if ziel is not None:
            tol = ruf(ziel.GetDimension2(0), "Tolerance")
            tol.Type = TOL_FIT
            werte["SetFitValues"] = tol.SetFitValues("H7", "")
            werte["SetText_suffix"] = ziel.SetText(TEXT_SUFFIX, " Ⓔ")
            ruf(drw, "EditRebuild3")
            werte["zurueck"] = mass_info(ziel)
        else:
            werte["ziel"] = "kein Maß 20 mm gefunden"
        ext = ruf(drw, "Extension")
        werte["sf_norm_vorher"] = ext.GetUserPreferenceInteger(SF_STANDARD, 0)
        werte["sf_norm_setzen"] = ext.SetUserPreferenceInteger(SF_STANDARD, 0, SF_21920)
        werte["sf_norm_nachher"] = ext.GetUserPreferenceInteger(SF_STANDARD, 0)
        v = views(drw)[0]
        x0, y0, x1, y1 = list(ruf(v, "GetOutline"))
        drw.ClearSelection2(True)
        sf = ext.InsertSurfaceFinishSymbol3(SF_MACHINING_REQ, LEADER_STRAIGHT, x1 + 0.01, y1, 0, 0, ARROW_CLOSED,
                                            "", "", "", "", "Ra 0,8", "", "")
        werte["sf_eingefuegt"] = sf is not None
        if sf is not None:
            werte["sf_text_0_9"] = [sf.GetText(i) for i in range(0, 10)]
        return werte
    q7()

    @frage("8_zuruecklesen")
    def q8():
        drw = zust["drw"]
        aus = {}
        for v in views(drw):
            aus[ruf(v, "GetName2")] = [mass_info(d) for d in anzeige_masse(v)]
        v = views(drw)[0]
        try:
            neu = ruf(v, "GetFirstDisplayDimension6")
            aus["GetFirstDisplayDimension6"] = "vorhanden" if neu is not None else "None"
        except Exception as e:
            aus["GetFirstDisplayDimension6"] = repr(e)[:200]
        try:
            aus["GetAnnotationsByType"] = len(v.GetAnnotationsByType(4) or ())
        except Exception as e:
            aus["GetAnnotationsByType"] = repr(e)[:200]
        return {"masse": aus}
    q8()

    @frage("9_speichern_pdf_zeit")
    def q9():
        drw = zust["drw"]
        ext = ruf(drw, "Extension")
        slddrw, pdf = ordner / "buchse_spike.SLDDRW", ordner / "buchse_spike.pdf"
        f, w = byref_long(), byref_long()
        t0 = time.time()
        ok1 = ext.SaveAs(str(slddrw), 0, SAVE_SILENT, callout_leer(), f, w)
        t1 = time.time()
        f2, w2 = byref_long(), byref_long()
        ok2 = ext.SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), f2, w2)
        return {"slddrw": ok1, "slddrw_s": round(t1 - t0, 2), "pdf": ok2, "pdf_s": round(time.time() - t1, 2),
                "pdf_bytes": pdf.stat().st_size if pdf.exists() else 0, "fehler": [f.value, f2.value],
                "sha_buchse_unveraendert": sha(buchse) == sha_buchse_vorher}
    q9()

    @frage("4b_spannplatte_bohrungsangabe")
    def q4b():
        drw, info = neue_zeichnung(platte)
        werte = {"blatt": info}
        for typen, schluessel in ((INS_MARKED, "markiert"), (INS_HOLE_CALLOUT, "bohrungsangabe")):
            vorher = sum(len(anzeige_masse(v)) for v in views(drw))
            t0 = time.time()
            je_ansicht = masse_einfuegen(drw, typen)
            nachher = sum(len(anzeige_masse(v)) for v in views(drw))
            werte[schluessel] = {"je_ansicht": je_ansicht, "masse_neu": nachher - vorher, "s": round(time.time() - t0, 2)}
        werte["masse_je_ansicht"] = {ruf(v, "GetName2"): [mass_info(d)["name"] + " = " + str(mass_info(d)["wert_mm"])
                                                          for d in anzeige_masse(v)] for v in views(drw)}
        werte["notizen_je_ansicht"] = {ruf(v, "GetName2"): len(ruf(v, "GetAnnotations") or ()) for v in views(drw)}
        f, w = byref_long(), byref_long()
        ruf(drw, "Extension").SaveAs(str(ordner / "spannplatte_spike.pdf"), 0, SAVE_SILENT, callout_leer(), f, w)
        app.CloseDoc(ruf(drw, "GetTitle"))
        return werte
    q4b()

    app.CloseAllDocuments(True)
    merke("ende", status="ok")


if __name__ == "__main__":
    AUS = Path(sys.argv[3]) / "spike-z1.json"
    Path(sys.argv[3]).mkdir(parents=True, exist_ok=True)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
