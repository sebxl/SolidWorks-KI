"""Testhelfer der Zeichnungsprüfung: baut ein Ist so, wie die Zeichnung sein soll (Plan Z1.4 Task 2).

Die Pläne kommen aus den Referenzen (`massplan`), nie von Hand kopiert."""

from swki.zeichnung.ist import Ist, IstAngabe, IstAnsicht, IstMass, IstToleranz
from swki.zeichnung.massplan import Mass, massplan
from swki.zeichnung.toleranzangaben import Toleranz
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


def ideal_ist(plan: list[Mass], ansichten: dict[str, str] | None = None) -> Ist:
    """Ideale Zeichnung zum Plan. `ansichten`: Name → Art (ansicht | schnitt | einzelheit), die erste nimmt die
    Maße und Notizen auf; Vorgabe {"haupt": "ansicht"}. Lineare Maße gleicher Richtung und gleichen Werts landen in
    je einer weiteren Ansicht „<erste><n>“ (zwei Maße mit denselben Endpunkten in einer Ansicht wären ein Doppelmaß)."""
    ansichten = ansichten or {"haupt": "ansicht"}
    erste = next(iter(ansichten))
    ist_ansichten = {name: IstAnsicht(name, None, art, "2:1" if art == "einzelheit" else "1:1",
                                      {"schnitt": "A-A", "einzelheit": "B"}.get(art))
                     for name, art in ansichten.items()}
    masse, angaben, gesehen = [], [], {}
    for m in plan:
        if m.quelle == "angabe":
            angaben.append(IstAngabe("hinweis", erste, m.text, None, None, ()))
            continue
        if m.quelle not in ("modell", "neu"):
            continue
        art = _IST_ART[m.art]
        tol = ist_toleranz(m.toleranz)
        praefix = m.praefix + {"durchmesser": "Ø", "radius": "R"}.get(art, "")
        suffix = m.suffix + (" Ⓔ" if m.toleranz is not None and m.toleranz.huelle else "")
        ansicht, richtung, punkte = erste, None, None
        if art == "laenge":
            n = gesehen[m.wert] = gesehen.get(m.wert, -1) + 1
            if n:
                ansicht = f"{erste}{n + 1}"
                ist_ansichten.setdefault(ansicht, IstAnsicht(ansicht, None, "ansicht", "1:1", None))
            richtung, punkte = "h", ((0.0, 0.0), (m.wert, 0.0))
        masse.append(IstMass(m.name or m.id, ansicht, art, m.wert, praefix, suffix, False, tol, richtung, punkte,
                             False if art == "laenge" else None))
    return Ist("A3", "1:1", tuple(ist_ansichten.values()), tuple(masse), tuple(angaben))
