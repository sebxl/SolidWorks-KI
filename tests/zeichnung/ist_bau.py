"""Testhelfer der Zeichnungsprüfung: baut ein Ist so, wie die Zeichnung sein soll (Plan Z1.4 Task 2).

Die Pläne kommen aus den Referenzen (`massplan`), nie von Hand kopiert."""

from swki.zeichnung.anforderungen_setzen import instanzen
from swki.zeichnung.ist import Ist, IstAngabe, IstAnsicht, IstMass, IstToleranz
from swki.zeichnung.massplan import Mass, massplan
from swki.zeichnung.toleranzangaben import SAMMEL_RAUHEIT, Toleranz, sammelangaben
from tests.zeichnung.test_massplan import _buchse_protokoll, _lade_ref, _spannplatte_protokoll

_IST_ART = {"laenge": "laenge", "lage": "laenge", "tiefe": "laenge", "abstand": "laenge", "paarabstand": "laenge",
            "fase": "laenge", "durchmesser": "durchmesser", "radius": "radius", "winkel": "winkel"}


def plan_spannplatte_z() -> list[Mass]:
    return massplan(_lade_ref("zeichnung/spannplatte_z.yaml"), _spannplatte_protokoll())


def plan_buchse_z() -> list[Mass]:
    return massplan(_lade_ref("zeichnung/buchse_z.yaml"), _buchse_protokoll())


def ist_toleranz(t: Toleranz | None) -> IstToleranz:
    if t is None:
        return IstToleranz("keine", None, None, None)
    if t.passung is not None:
        return IstToleranz("passung", t.passung, None, None)
    typ = "symmetrisch" if abs(t.oben + t.unten) < 1e-9 else "bilateral"
    return IstToleranz(typ, None, t.oben, t.unten)


def schriftfeld_eigenschaften(spec: dict) -> dict[str, str]:
    """Eigenschaften einer idealen Zeichnung (Namen wie `zeichnung.schriftfeld` in config/standard.yaml, Eigentümer
    und Freigegeben leer). „Blatt“ fehlt wie beim Rückleser: den Blattzähler setzt SolidWorks, der Rückleser erfindet
    ihn nicht (Review 4b, M5; `pruefe_schriftfeld`: nicht geprüft)."""
    eig = spec.get("eigenschaften") or {}
    return {"Zeichnungsnummer": eig.get("Zeichnungsnummer", spec["name"]), "Benennung": eig.get("Benennung", spec["name"]),
            "DrawnBy": "swki", "DrawnDate": "27.11.2026", "Dokumentart": "Einzelteilzeichnung", "Freigegeben": ""}


def ideal_ist(plan: list[Mass], ansichten: dict[str, str] | None = None, spec: dict | None = None,
              eigenschaften: dict[str, str] | None = None) -> Ist:
    """Ideale Zeichnung zum Plan. `ansichten`: Name → Art (ansicht | schnitt | einzelheit), die erste nimmt die
    Maße und Notizen auf; Vorgabe {"haupt": "ansicht"}. Alle Maße liegen in dieser Ansicht, alle starten bei 0.
    Mit `spec`: Sammelangaben (je Zeile eine Notiz, dazu die Sammelrauheit) und die Schriftfeld-Eigenschaften
    (`eigenschaften` überschreibt sie). Rauheit, Form/Lage und Bezüge des Plans stehen mit Merkmal im Ist."""
    ansichten = ansichten or {"haupt": "ansicht"}
    erste = next(iter(ansichten))
    ist_ansichten = {name: IstAnsicht(name, None, art, "2:1" if art == "einzelheit" else "1:1",
                                      {"schnitt": "A-A", "einzelheit": "Z"}.get(art))
                     for name, art in ansichten.items()}
    masse, angaben = [], []
    for m in plan:
        if m.quelle == "angabe":
            angaben.append(IstAngabe("hinweis", erste, m.text, None, None, ()))
            continue
        if m.quelle == "rauheit":
            angaben.append(IstAngabe("rauheit", erste, m.text, None, None, (), m.merkmal))
            continue
        if m.quelle == "form_lage":
            n = instanzen(spec, m.merkmal) if spec is not None else 1  # „n ד über dem Rahmen (Task 4b)
            angaben.append(IstAngabe("form_lage", erste, f"{m.form_lage.symbol} {m.text}", m.form_lage.symbol, m.text,
                                     m.form_lage.bezug, m.merkmal, n if n > 1 else None))
            continue
        if m.quelle == "bezug":
            angaben.append(IstAngabe("bezug", erste, m.text, None, None, (m.text,), m.merkmal))
            continue
        if m.quelle not in ("modell", "neu"):
            continue
        art = _IST_ART[m.art]
        tol = ist_toleranz(m.toleranz)
        praefix = m.praefix + {"durchmesser": "Ø", "radius": "R"}.get(art, "")
        suffix = m.suffix + (" Ⓔ" if m.toleranz is not None and m.toleranz.huelle else "")
        ansicht, richtung, punkte = erste, None, None
        if art == "laenge":
            richtung, punkte = "h", ((0.0, 0.0), (m.wert, 0.0))
        masse.append(IstMass(m.name or m.id, ansicht, art, m.wert, praefix, suffix, False, tol, richtung, punkte,
                             False if art == "laenge" else None))
    if spec is not None:
        angaben += [IstAngabe("hinweis", erste, zeile, None, None, ()) for zeile in sammelangaben(spec)]
        angaben.append(IstAngabe("hinweis", erste, SAMMEL_RAUHEIT, None, None, ()))
    eig = {**schriftfeld_eigenschaften(spec), **(eigenschaften or {})} if spec is not None else dict(eigenschaften or {})
    return Ist("A3quer", "1:1", tuple(ist_ansichten.values()), tuple(masse), tuple(angaben), eig)
