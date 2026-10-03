"""Passung Normteil ↔ Bohrung bei konzentrischen Verknüpfungen (Spec 3b §5.7), ohne SolidWorks."""

from swki.baugruppe.modell import Quelle
from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.normen import groesse_text

INNEN = {"ISO 4762": "d", "ISO 4032": "d", "ISO 7089": "d1"}  # Schaft- bzw. Innen-Ø je Norm (Tabellenmaß)


def passt(q: Quelle, f: dict, parameter: dict) -> str | None:
    """None, wenn Normteil q auf die Bohrung f passt; sonst eine Meldung."""
    norm, groesse = q.norm, q.groesse
    if f["typ"] == "normbohrung":
        art, g = f["art"], groesse_text(f["groesse"])
        if norm == "ISO 4762":
            ok = art in ("zylinderschraube", "gewinde") and g == groesse
        elif norm == "ISO 8734":
            ok = art == "stift" and g == groesse
        elif norm in ("ISO 7089", "ISO 4032"):
            ok = art != "stift" and g == groesse
        else:
            ok = False
        return None if ok else f"{norm} {groesse} passt nicht auf normbohrung {art} {g}"
    if norm not in INNEN:
        return f"{norm} {groesse} gehört nicht in eine freie Bohrung (nur normbohrung stift)"
    try:
        d = auswerten(f["durchmesser"], parameter)
    except AusdruckFehler:
        return None  # meldet die Prüfung der Teil-Spec
    innen = q.masse[INNEN[norm]]
    ok = d > innen if norm == "ISO 4762" else d >= innen
    return None if ok else f"{norm} {groesse}: Bohrung Ø {d:g} zu klein (Schaft-/Innen-Ø {innen:g})"


def _paar(v: dict, quellen: dict[str, Quelle]):
    """(Normteil, Eigenteil, Seite des Eigenteils), wenn v die EINBAU_ACHSE eines Normteils mit einer Bohrungsachse
    verbindet; sonst None."""
    for n, t in (("a", "b"), ("b", "a")):
        qn, qt = quellen.get(v[n]["komponente"]), quellen.get(v[t]["komponente"])
        if (qn is not None and qt is not None and qn.art == "normteil" and v[n].get("referenz") == "EINBAU_ACHSE"
                and qt.art == "teil" and v[t].get("achse")):
            return qn, qt, v[t]
    return None


def passung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    for i, v in enumerate(spec.get("verknuepfungen", [])):
        if v["typ"] != "konzentrisch" or (paar := _paar(v, quellen)) is None:
            continue
        qn, qt, seite = paar
        f = next((x for x in qt.spec["features"] if x["id"] == seite["feature"]), None)
        if f is None or f["typ"] not in ("normbohrung", "bohrung"):
            continue
        if meldung := passt(qn, f, qt.spec.get("parameter", {})):
            befunde.append({"pfad": f"verknuepfungen[{i}]", "meldung": f"Passung: {meldung}"})
    return befunde
