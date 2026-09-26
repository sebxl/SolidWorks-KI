"""S5: Zwei Kästen in Baugruppe, überlappend und nicht überlappend, Kollisionsprüfung."""

from spikes._gemeinsam import kasten, lauf, neue_baugruppe, neues_teil, schliesse, speichere, standardebenen, start
from swki.verbindung import callout_leer, mm, wert


def _teil(app, r, pfad):
    model = neues_teil(app, r)
    kasten(model, standardebenen(model)[1], 100, 60, 20)
    fehler = speichere(model, pfad)
    if fehler:
        raise RuntimeError(f"Speichern {pfad}: Fehler {fehler}")
    return model


def _zaehle(assy) -> int:
    # InterferenceDetectionManager: nullargumentige Property, liefert direkt das IInterferenceDetectionMgr-
    # Objekt (Bindungs-Eigenart, siehe spikes/_gemeinsam.py) – reiner Attributzugriff, kein "()".
    idm = assy.InterferenceDetectionManager
    try:
        return int(wert(idm.GetInterferenceCount))
    finally:
        idm.Done()


def pruefen() -> dict:
    r, app = start()
    ordner = r.arbeitsordner / "stufe0" / "s5"
    teil = _teil(app, r, ordner / "kasten.sldprt")  # bleibt geöffnet, AddComponent braucht es im Speicher
    assy = neue_baugruppe(app, r)
    try:
        pfad = str(ordner / "kasten.sldprt")
        c1 = assy.AddComponent5(pfad, 0, "", False, "", 0.0, 0.0, 0.0)
        c2 = assy.AddComponent5(pfad, 0, "", False, "", mm(50), 0.0, 0.0)
        ueberlappend = _zaehle(assy)
        # IComponent2.Select4: Data ist ein SelectData-Objekt (System.Object). Rohes Python None
        # löst com_error "Typenkonflikt" aus (gleiche Eigenart wie FullyDefineSketch in S3) –
        # callout_leer() (leeres VT_DISPATCH-VARIANT) statt None übergeben.
        c2.Select4(False, callout_leer(), False)
        assy.EditDelete()
        c3 = assy.AddComponent5(pfad, 0, "", False, "", mm(150), 0.0, 0.0)
        frei = _zaehle(assy)
        return {
            "abweichungen": [
                "InterferenceDetectionManager (IAssemblyDoc) wird wie FirstFeature in "
                "_gemeinsam.py als reiner Attributzugriff ohne '()' aufgerufen "
                "(Bindungs-Eigenart, siehe docs/stufe0/ergebnisse/s2_ebenen.json).",
                "IComponent2.Select4: Data-Parameter (SelectData) mit callout_leer() statt "
                "rohem Python None übergeben, sonst com_error 'Typenkonflikt' (wie FullyDefineSketch in S3).",
            ],
            "komponenten_ok": all(c is not None for c in (c1, c2, c3)),
            "kollisionen_ueberlappend": ueberlappend,
            "kollisionen_frei": frei,
        }
    finally:
        schliesse(app, assy)
        schliesse(app, teil)


if __name__ == "__main__":
    lauf("s5_kollision", pruefen)
