"""Spike Z1.3 Stufe 4, Teil g (Review Task 5, I6): Wo steht der Text eines Rauheitssymbols, und woher kommt der lose
Strich über dem Dreieck?

Je Variante der Dokumenteinstellung „Oberflächensymbol-Norm“ (`swDetailingSFSymbolStandard` = 629:
0 = ISO 1302:1992, 1 = ISO 1302:2002, 2 = ISO 21920-1; Toggle `swDetailingDisplaySFSymbolsPer2002` = 222) eine Kopie
der Zeichnung: ein freies Symbol (ohne Hinweislinie) mit den Markern M1…M7 in den sieben Textplätzen von
`InsertSurfaceFinishSymbol3` (MachAllowance, OtherVals, ProdMethod, SampleLen, MaxRoughness, MinRoughness,
RoughnessSpacing) und je ein Symbol mit nur „Ra 0,8“ an Platz 1…7. PDF und Ausschnitte zur Durchsicht.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4g <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import hashlib
import json
import sys
from pathlib import Path

from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

SF_NORM, SF_2002 = 629, 222        # swUserPreferenceIntegerValue_e / swUserPreferenceToggle_e
OHNE_OPTION = 0                    # swDetailingNoOptionSpecified
SF_BEARBEITET, OHNE_FUEHRUNG, PFEIL = 1, 0, 1


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    sha_teil = sha(teil)
    werte = {}
    for norm in (None, 0, 1, 2):
        f, w = byref_long(), byref_long()
        drw = app.OpenDoc6(str(pfad), 3, 1, "", f, w)
        ext = _ruf(drw, "Extension")
        name = f"vorlage" if norm is None else f"norm{norm}"
        werte[name] = {"norm_vorher": ext.GetUserPreferenceInteger(SF_NORM, OHNE_OPTION),
                       "per2002_vorher": ext.GetUserPreferenceToggle(SF_2002, OHNE_OPTION)}
        if norm is not None:
            werte[name]["gesetzt"] = ext.SetUserPreferenceInteger(SF_NORM, OHNE_OPTION, norm)
        _ruf(drw, "EditSheet")
        drw.ClearSelection2(True)
        texte = [f"M{i}" for i in range(1, 8)]
        sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, OHNE_FUEHRUNG, 0.30, 0.15, 0, 0, PFEIL, *texte)
        if sf is not None:
            _ruf(sf, "GetAnnotation").SetPosition2(0.30, 0.15, 0)
        for platz in range(7):
            texte = [""] * 7
            texte[platz] = "Ra 0,8"
            drw.ClearSelection2(True)
            s = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, OHNE_FUEHRUNG, 0.25 + 0.025 * platz, 0.11, 0, 0, PFEIL,
                                               *texte)
            if s is not None:
                _ruf(s, "GetAnnotation").SetPosition2(0.25 + 0.025 * platz, 0.11, 0)
        # Teil g2: ISFSymbol.SetText(swSurfaceFinishSymbolText_e 1…10, „Ra 0,8“) an leeren Symbolen, Zeile y = 80 mm
        werte[name]["settext"] = {}
        for welche in range(1, 11):
            drw.ClearSelection2(True)
            s = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, OHNE_FUEHRUNG, 0.03 + 0.022 * welche, 0.08, 0, 0, PFEIL,
                                               *([""] * 7))
            if s is None:
                continue
            _ruf(s, "GetAnnotation").SetPosition2(0.03 + 0.022 * welche, 0.08, 0)
            werte[name]["settext"][welche] = (s.SetText(welche, "Ra 0,8"), s.GetText(welche))
        werte[name]["norm_nachher"] = ext.GetUserPreferenceInteger(SF_NORM, OHNE_OPTION)
        _ruf(drw, "EditRebuild3")
        pdf = pfad.with_name(pfad.stem + f"_s4g_{name}.pdf")
        ext.SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
        for d in list(app.GetDocuments or ()):
            if "Z1S4-" in d.GetPathName:
                app.CloseDoc(d.GetTitle)
        import pymupdf
        pt = 72 / 25.4
        with pymupdf.open(pdf) as doc:
            s = doc[0]
            h = s.rect.height / pt
            for nr, (x, y, r) in enumerate(((300, 155, 14), (325, 115, 80), (155, 85, 125))):
                clip = pymupdf.Rect((x - r) * pt, (h - y - r * (0.5 if nr else 1)) * pt, (x + r) * pt,
                                    (h - y + r * (0.5 if nr else 1)) * pt)
                s.get_pixmap(dpi=300, clip=clip).save(str(pdf.with_name(pdf.stem + f"_{nr}.png")))
            werte[name]["texte"] = [(b[4].strip(), [round(v / pt, 1) for v in b[:4]]) for b in s.get_text("blocks")
                                    if "M" in b[4] or "Ra" in b[4]]
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
