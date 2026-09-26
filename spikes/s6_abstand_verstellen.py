"""S6: Abstandsverknüpfung zwischen zwei Kästen verstellen und Position messen."""

from spikes._gemeinsam import kasten, lauf, neue_baugruppe, neues_teil, schliesse, speichere, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import byref_long, in_mm, mm, wert


def _e(db, name):
    return {e["name"]: e["wert"] for e in enum(db, name)}


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    mate, align, sel = _e(db, "swMateType_e"), _e(db, "swMateAlign_e"), _e(db, "swSelectType_e")
    ordner = r.arbeitsordner / "stufe0" / "s6"
    teil = neues_teil(app, r)
    kasten(teil, standardebenen(teil)[1], 40, 40, 20)  # Kasten lokal y=0..20mm (Extrusionsrichtung)
    pfad_teil = ordner / "block.sldprt"
    fehler = speichere(teil, pfad_teil)
    if fehler:
        raise RuntimeError(f"Speichern {pfad_teil}: Fehler {fehler}")
    assy = neue_baugruppe(app, r)
    try:
        pfad = str(pfad_teil)
        # AddComponent5 X/Y/Z ist laut API-Doku ("X coordinate of the component center") das
        # Zentrum der Bauteil-Bounding-Box, nicht dessen Ursprung (Abweichung zur Brief-Annahme
        # "erste = fixiert [am Ursprung]"/"y=50..70mm", siehe "abweichungen" unten). Bei einem
        # lokal y=0..20mm hohen Kasten (Zentrum bei lokal y=10mm) landet der Bauteil-Ursprung
        # (Transform2-Translation) daher 10mm unterhalb der angeforderten Y-Koordinate.
        unten = assy.AddComponent5(pfad, 0, "", False, "", 0.0, 0.0, 0.0)          # Zentrum bei y=0
        oben = assy.AddComponent5(pfad, 0, "", False, "", 0.0, mm(50), 0.0)        # Zentrum bei y=50mm
        ext = assy.Extension
        assy.ClearSelection2(True)
        a = ext.SelectByRay(mm(5), mm(30), mm(5), 0.0, -1.0, 0.0, mm(0.5), sel["swSelFACES"], False, 1, 0)
        b = ext.SelectByRay(mm(5), mm(40), mm(5), 0.0, 1.0, 0.0, mm(0.5), sel["swSelFACES"], True, 1, 0)
        fehler = byref_long()
        m = assy.AddMate5(mate["swMateDISTANCE"], align["swMateAlignCLOSEST"], False, mm(30), mm(30), mm(30),
                          1, 1, 0.0, 0.0, 0.0, False, False, 0, fehler)
        messungen = []
        for soll in (30, 10, 60):
            # DisplayDimension2(Index)/GetDimension2(Index) sind index-parametrierte Getter, die
            # ein COM-Objekt liefern; sie werden regulär mit "(index)" aufgerufen (kein reiner
            # Attributzugriff nötig/möglich, da ein Argument verlangt wird).
            dim = m.DisplayDimension2(0).GetDimension2(0)
            dim.SetSystemValue3(mm(soll), 1, None)
            # IModelDoc2.EditRebuild3 ist nullargumentig: pywin32 ruft es schon beim Attributzugriff
            # auf und liefert direkt das bool-Ergebnis (Bindungs-Eigenart, siehe _gemeinsam.py). Ein
            # zusätzliches "()" (wie im Brief-Snippet) scheitert mit
            # TypeError("'bool' object is not callable"), da das bool-Ergebnis kein Default-Member hat.
            assy.EditRebuild3
            y_mm = in_mm(oben.Transform2.ArrayData[10])
            # erwartet: unten bleibt fixiert, seine Oberkante liegt (wegen der Zentrum-Platzierung,
            # s.o.) bei lokal y=20mm minus 10mm Versatz = 10mm; die Distanzverknüpfung hält den
            # Abstand zwischen dieser Kante und obens Unterkante (= obens Transform2-Y) auf "soll".
            messungen.append({"soll_abstand": soll, "y_ursprung_oben_mm": round(y_mm, 4), "erwartet": 10 + soll})
        return {
            "abweichungen": [
                "AddComponent5 X/Y/Z ist laut API-Doku das Zentrum der Bauteil-Bounding-Box, "
                "nicht dessen Ursprung (im Brief als Ursprung angenommen, Kommentare 'erste = "
                "fixiert'/'y=50..70mm'). Deshalb 'erwartet' als '10 + soll' statt '20 + soll' "
                "berechnet (10mm = halbe Kastentiefe = Versatz zwischen Zentrum und Ursprung); "
                "live per Transform2 vor/nach dem Mate nachgemessen, siehe Bericht.",
                "IModelDoc2.EditRebuild3 ist nullargumentig und liefert bereits beim "
                "Attributzugriff das bool-Ergebnis (gleiche Bindungs-Eigenart wie FirstFeature "
                "in _gemeinsam.py); der Aufruf mit '()' aus dem Brief scheitert mit "
                "TypeError(\"'bool' object is not callable\") und wurde durch reinen "
                "Attributzugriff ersetzt.",
            ],
            "auswahl": [bool(a), bool(b)], "mate_ok": m is not None, "fehlerstatus": fehler.value,
            "messungen": messungen, "unten_fixiert": bool(wert(unten.IsFixed)),
        }
    finally:
        schliesse(app, assy)
        schliesse(app, teil)


if __name__ == "__main__":
    lauf("s6_abstand_verstellen", pruefen)
