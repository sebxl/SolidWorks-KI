"""Spike Z1.0 Nachtrag: Blattformate (.slddrt, Kopien im Arbeitsordner) in eine leere Zeichnung laden und Schriftfeld-
Notizen samt Eigenschaftsverknüpfung ($PRP/$PRPSHEET) auslesen. Wegwerf; speichert nichts.

    .venv\\Scripts\\python.exe -m spikes.z1_blattformat_lesen <ordner mit .slddrt> <ausgabe.json>
"""

import json
import sys
from pathlib import Path

from spikes.s9a_gemeinsam import start
from spikes.s9b_gemeinsam import byref_long
from spikes.z1_zeichnung import SAVE_SILENT, SW_DEFAULT_TEMPLATE_DRAWING, ruf
from swki.verbindung import callout_leer

PAPIER = {"a3 quer": (8, 0.42, 0.297), "a4 quer": (6, 0.297, 0.21), "a4 din": (7, 0.21, 0.297), "a3 - iso": (8, 0.42, 0.297), "a4 - iso": (7, 0.21, 0.297)}  # swDwgPaperSizes_e
VORLAGE_EIGEN = 12  # swDwgTemplates_e.swDwgTemplateCustom


def main(ordner: Path, aus: Path) -> None:
    r, app = start()
    vorlage = app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING)
    ergebnis = {}
    for datei in sorted(d for d in ordner.glob("*.slddrt") if not d.name.startswith("~$")):
        papier, breite, hoehe = next(v for k, v in PAPIER.items() if datei.name.lower().startswith(k))
        drw = app.NewDocument(vorlage, 0, 0, 0)
        sheet = ruf(drw, "GetCurrentSheet")
        ok = drw.SetupSheet5(ruf(sheet, "GetName"), papier, VORLAGE_EIGEN, 1, 1, True, str(datei), breite, hoehe,
                             "Standard", True)  # IDrawingDoc.SetupSheet5 (11, 2009)
        sheet = ruf(drw, "GetCurrentSheet")
        notizen = []
        blattansicht = ruf(drw, "GetFirstView")  # erste "Ansicht" ist das Blatt mit Blattformat
        note = ruf(blattansicht, "GetFirstNote")
        while note is not None:
            pt = list(ruf(note, "GetTextPoint2") or ())
            notizen.append({"text": ruf(note, "GetText"), "verknuepft": ruf(note, "PropertyLinkedText"),
                            "lage_mm": [round(x * 1000, 1) for x in pt[:2]]})
            note = ruf(note, "GetNext")
        anns = list(ruf(blattansicht, "GetAnnotations") or ())
        notes2 = list(ruf(blattansicht, "GetNotes") or ())
        for n in notes2:
            notizen.append({"text": ruf(n, "GetText"), "verknuepft": ruf(n, "PropertyLinkedText"), "quelle": "GetNotes"})
        f, w = byref_long(), byref_long()
        ruf(drw, "Extension").SaveAs(str(aus.parent / (datei.stem + ".pdf")), 0, SAVE_SILENT, callout_leer(), f, w)
        ergebnis[datei.name + " ann"] = {"annotationen": len(anns), "getnotes": len(notes2),
                                         "blattformat_name": ruf(sheet, "GetSheetFormatName")}
        ergebnis[datei.name] = {"SetupSheet5": ok, "vorlage_gesetzt": ruf(sheet, "GetTemplateName"),
                                "blatt": list(ruf(sheet, "GetProperties2") or ()), "notizen": notizen}
        print(datei.name, len(notizen), "Notizen", flush=True)
        app.CloseDoc(ruf(drw, "GetTitle"))
    aus.write_text(json.dumps(ergebnis, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
