"""Gespeichertes (selbst gebautes) Teil öffnen und untersuchen, ohne zu speichern.

Immer: Gleichungen (mit Status), Feature-Baum, What's Wrong. Je --feature zusätzlich: Unterfeatures, Skizzen (Status,
Punkte, Segmente, Beziehungen – deckungsgleiche mit ihren Elementen –, Maße mit treibend/getrieben), Flächen des
Features (Zylinder mit Achse und Radius) und beim Bohrungsassistenten Typ und Größe.

Herkunft: Diagnose sporadischer Normbohrungsfehler (REPRO-NB) und gefangener Deckungsbeziehungen an Langlöchern (AP 6.8
Durchlicht, Fix 1cf6d7e).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.inspiziere <teil.sldprt> [--feature NAME …] [--rebuild]
"""

import argparse
from pathlib import Path

from swki.compiler import sw
from swki.compiler.topologie import flaechen
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import byref_variant, in_mm, verbinde

SW_DECKUNGSGLEICH = 9  # swConstraintType_e.swConstraintType_COINCIDENT (wie swki.compiler.skizze)


def element_text(e) -> str:
    try:
        return f"Punkt ({in_mm(e.X):.3f}, {in_mm(e.Y):.3f})"
    except Exception:
        try:
            return f"Segment Typ {e.GetType}, Konstruktion {e.ConstructionGeometry}"
        except Exception:
            return repr(e)


def skizze_zeigen(feat, einzug: str = "   ") -> None:
    sk = feat.GetSpecificFeature2
    print(f"{einzug}Skizze {feat.Name}: Status {sk.GetConstrainedStatus}")
    for p in sk.GetSketchPoints2 or ():
        print(f"{einzug}  Punkt ({in_mm(p.X):.4f}, {in_mm(p.Y):.4f}, {in_mm(p.Z):.4f}) Typ {p.Type}")
    for s in sk.GetSketchSegments or ():
        print(f"{einzug}  Segment Typ {s.GetType}, Länge {in_mm(s.GetLength):.4f} mm, Konstruktion {s.ConstructionGeometry}")
    for r in sk.RelationManager.GetRelations(0) or ():
        elemente = r.GetEntities or ()
        print(f"{einzug}  Beziehung Typ {r.GetRelationType}, {len(elemente)} Elemente")
        if r.GetRelationType == SW_DECKUNGSGLEICH:
            for e, t in zip(elemente, r.GetEntitiesType or ()):
                print(f"{einzug}    deckungsgleich: Element Typ {t}: {element_text(e)}")
    dd = feat.GetFirstDisplayDimension
    while dd is not None:
        d = dd.GetDimension2(0)
        print(f"{einzug}  Maß {d.FullName} = {in_mm(d.SystemValue):.4f} mm, treibend {d.DrivenState}")
        dd = feat.GetNextDisplayDimension(dd)


def feature_zeigen(f) -> None:
    if f.GetTypeName2 == "ProfileFeature":
        skizze_zeigen(f)
    sub = f.GetFirstSubFeature
    while sub is not None:
        print(f"  Unterfeature {sub.Name} ({sub.GetTypeName2})")
        if sub.GetTypeName2 == "ProfileFeature":
            skizze_zeigen(sub)
        sub = sub.GetNextSubFeature
    for fl in flaechen(f):
        if fl.art == "zylinder":
            print(f"  Zylinder Punkt {tuple(round(c, 3) for c in fl.punkt)} Achse {fl.achse} r={fl.radius:.3f}")
        else:
            print(f"  Fläche {fl.art} {tuple(round(c, 3) for c in fl.punkt)}")
    if f.GetTypeName2 == "HoleWzd":
        hw = f.GetDefinition
        print("  Bohrungsassistent: Typ", hw.Type, "Größe", hw.FastenerSize)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("teil", type=Path)
    a.add_argument("--feature", action="append", default=[], help="Feature im Detail zeigen (mehrfach möglich)")
    a.add_argument("--rebuild", action="store_true", help="vorher ForceRebuild3(False)")
    args = a.parse_args()
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, args.teil)
    try:
        if args.rebuild:
            print("ForceRebuild3:", model.ForceRebuild3(False))
        eq = model.GetEquationMgr
        print("Gleichungen (Status", eq.Status, "):")
        for i in range(eq.GetCount):
            print(f"  {eq.Equation(i)}  -> {eq.Value(i)}")
        f = model.FirstFeature
        while f is not None:
            print(f"Feature {f.Name} ({f.GetTypeName2})")
            if f.Name in args.feature:
                feature_zeigen(f)
            f = f.GetNextFeature
        print("What's Wrong:", model.Extension.GetWhatsWrongCount)
        fe, code, warnung = byref_variant(), byref_variant(), byref_variant()
        model.Extension.GetWhatsWrong(fe, code, warnung)
        for x, c, w in zip(fe.value or (), code.value or (), warnung.value or ()):
            print(f"  {x.Name}: Code {c}, nur Warnung {w}")
    finally:
        sw.schliesse(app, model)


if __name__ == "__main__":
    main()
