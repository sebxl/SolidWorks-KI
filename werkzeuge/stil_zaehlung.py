"""Konstruktionsstil zählen (Paket Konstruktionsstil, ohne SolidWorks): Feature-Typen und validieren-Hinweise je Art
über alle Teil-Specs der genannten Ordner – Ausgangs- und Endmaß für docs/konstruktionsstil/ergebnisse.md.

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.stil_zaehlung <ordner> … [--je-spec]   (Ausgabe JSON)
Freigegebene Kopien und Protokolle zählen nicht; Specs, die sich nicht laden lassen, stehen unter `fehler`.
"""

import argparse
import collections
import json
from pathlib import Path

from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec


def zaehle(ordner: list[Path]) -> dict:
    typen: collections.Counter = collections.Counter()
    arten: collections.Counter = collections.Counter()
    je_spec, fehler = {}, {}
    for wurzel in ordner:
        for pfad in sorted(wurzel.rglob("*.yaml")):
            if pfad.name.endswith(".freigegeben.yaml") or "protokolle" in pfad.parts:
                continue
            try:
                spec = lade_spec(pfad)
            except Exception as e:  # andere YAML (Baugruppen, Kaufteile, sim) oder ungültig
                if "art: teil" in pfad.read_text(encoding="utf-8"):
                    fehler[str(pfad)] = str(e)[:200]
                continue
            if spec.get("art") != "teil":
                continue
            t = collections.Counter(f["typ"] for f in spec["features"])
            h = collections.Counter(x["art"] for x in hinweise(spec))
            typen.update(t)
            arten.update(h)
            je_spec[str(pfad.relative_to(wurzel.parent))] = {"typen": dict(t), "hinweise": dict(h)}
    return {"specs": len(je_spec), "features": sum(typen.values()), "typen": dict(typen.most_common()),
            "hinweise": dict(arten.most_common()), "je_spec": je_spec, "fehler": fehler}


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("ordner", nargs="+", type=Path)
    a.add_argument("--je-spec", action="store_true", help="Zählung je Spec mit ausgeben")
    args = a.parse_args()
    erg = zaehle(args.ordner)
    if not args.je_spec:
        erg.pop("je_spec")
    print(json.dumps(erg, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
