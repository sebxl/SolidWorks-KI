"""Hinweise zu einer gültigen Baugruppen-Spezifikation (Spec 3b §5.8); sie blockieren nie."""

from swki.baugruppe.aufloesen import basis
from swki.baugruppe.modell import Baugruppe
from swki.konfig import lade_standard
from swki.spec.hinweise import hinweise as teil_hinweise

PRUEFAUFWAND_AB = 4  # Bewegungen; Spec 4a §4.4


def _drehlage_hinweise(bg: Baugruppe) -> list[dict]:
    """Konzentrisch mit Drehsperre (Vorgabe bei Kaufteilen) und dazu eine Verknüpfung der Drehlage desselben Kaufteils
    (Einbaureferenz ebene_durch_achse) wäre überbestimmt (Spec 3c §8.1). Gilt nur für Verknüpfungen auf eine Einbaureferenz,
    nicht für Gewindepositionen."""
    vs = bg.spec.get("verknuepfungen", [])
    drehlage = {}
    for v in vs:
        for s in ("a", "b"):
            q = bg.quellen.get(basis(v[s]["komponente"]))
            if q is not None and q.art == "kaufteil" and \
                    "ebene_durch_achse" in q.eintrag["einbau"].get(v[s].get("referenz"), {}):
                drehlage.setdefault(basis(v[s]["komponente"]), v["id"])
    ergebnis = []
    for i, v in enumerate(vs):
        if v["typ"] != "konzentrisch" or v.get("drehung_sperren") is False:
            continue
        for s in ("a", "b"):
            k = basis(v[s]["komponente"])
            # nur Einbaureferenzen des Kaufteils; eine Schraube in der Gewindeposition (gewinde) sperrt nur ihre eigene Drehung
            if k in drehlage and "referenz" in v[s]:
                ergebnis.append({"art": "drehlage_doppelt", "pfad": f"verknuepfungen[{i}].drehung_sperren",
                                 "meldung": f"{k}: Drehlage über {drehlage[k]} verknüpft – hier drehung_sperren: false "
                                            "setzen, sonst überbestimmt"})
    return ergebnis


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
    ergebnis += _drehlage_hinweise(bg)
    bws = bg.spec.get("bewegungen", [])
    if len(bws) >= PRUEFAUFWAND_AB:
        vorgabe = lade_standard()["bewegung_schritte"]
        stellungen = sum(b.get("schritte", vorgabe) + 1 for b in bws)
        ergebnis.append({"art": "pruefaufwand", "pfad": "bewegungen",
                         "meldung": f"{len(bws)} Bewegungen: {stellungen} Stellungen in Grundstellung, im ungünstigsten "
                                    f"Fall {len(bws) * stellungen} mit Paarläufen – Zeit und SolidWorks-Speicher beachten"})
    return ergebnis
