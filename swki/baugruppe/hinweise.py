"""Hinweise zu einer gültigen Baugruppen-Spezifikation (Spec 3b §5.8); sie blockieren nie."""

from swki.baugruppe.modell import Baugruppe
from swki.spec.hinweise import hinweise as teil_hinweise


def hinweise_baugruppe(bg: Baugruppe) -> list[dict]:
    ergebnis = []
    for datei, teil in bg.teile.items():
        komponente = bg.komponente_von(datei)
        ergebnis += [{**h, "pfad": f"{komponente}: {h['pfad']}"} for h in teil_hinweise(teil)]
    for i, v in enumerate(bg.spec.get("verknuepfungen", [])):
        for s in ("a", "b"):
            if "nahe" in v[s]:
                ergebnis.append({"art": "nahe", "pfad": f"verknuepfungen[{i}].{s}",
                                 "meldung": "Punktanker in einer Verknüpfung: bevorzugt referenz, {feature, flaeche} "
                                            "oder Bohrungsachse"})
        w = v.get("wert")
        if isinstance(w, (int, float)) and not isinstance(w, bool) and w != 0:
            ergebnis.append({"art": "feste_zahl", "pfad": f"verknuepfungen[{i}].wert",
                             "meldung": f"feste Zahl {w:g}: als Parameter führen, wenn der Wert eine Anforderung ist "
                                        "(sonst deckt die Freigabe ihn nicht ab)"})
    return ergebnis
