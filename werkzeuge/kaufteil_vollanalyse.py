"""Vollanalyse einer Hersteller-STEP vor dem Katalogeintrag: importieren (nichts speichern), je Volumen- und
Flächenkörper Hüllquader, Check3-Fehler, Flächenarten, nicht ebene/zylindrische Flächen, Zylinder- und Ebenenübersicht.

Ergänzt `swki kaufteil untersuchen` (Flächenübersicht des ganzen Teils) um die Sicht je Körper – nützlich bei
Herstellermodellen mit Körperfehlern oder Flächenkörpern (AP 6.8 Kamera/Objektiv/Durchlicht, UEBERGABE §9).
Die STEP nur lesen (Kopie im Quellordner der kaufteilbibliothek bzw. Datei des Nutzers), Ergebnis außerhalb des Repos.

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.kaufteil_vollanalyse <datei.step> <ausgabe.json> [--koerper 1,3]
--koerper: nur für diese Körper (Nummern) Zylinder, Ebenen und sonstige Flächen ausgeben (Übersicht immer für alle).
"""

import argparse
import json
import math
import sys
from pathlib import Path

from swki.compiler import sw
from swki.compiler.topologie import flaeche_aus, koerper
from swki.kaufteile import sw_kaufteil
from swki.kaufteile.diagnose import uebersicht
from swki.konfig import lade_rechner
from swki.verbindung import in_mm, verbinde

SW_FLAECHENKOERPER = 1  # swBodyType_e.swSheetBody


def _fehlerzahl(b) -> int:
    fe = b.Check3
    return 0 if fe is None else int(fe.Count)


def analysiere(step: Path) -> dict:
    app = verbinde(lade_rechner().sw_jahr)
    model = sw_kaufteil.importiere(app, step)
    try:
        erg = {"datei": str(step), "koerper": [], "flaechenkoerper": []}
        for i, b in enumerate(koerper(model), start=1):
            fl = [flaeche_aus(f) for f in (b.GetFaces() or ())]
            arten = {}
            for f in fl:
                arten[f.art] = arten.get(f.art, 0) + 1
            sonst = [{"id": f.objekt.GetSurface.Identity, "box": [round(in_mm(c), 2) for c in f.objekt.GetBox],
                      "A": round(f.objekt.GetArea * 1e6, 2)} for f in fl if f.art not in ("ebene", "zylinder")]
            ue = uebersicht(sw_kaufteil.datensaetze(fl), grenze=5000)
            erg["koerper"].append({"nr": i, "name": b.Name, "check3": _fehlerzahl(b),
                                   "box": [round(in_mm(c), 3) for c in b.GetBodyBox()], "flaechen": len(fl),
                                   "arten": arten, "sonstige": sonst, "zylinder": ue["zylinder"], "ebenen": ue["ebenen"]})
        for b in model.GetBodies2(SW_FLAECHENKOERPER, False) or ():
            erg["flaechenkoerper"].append({"name": b.Name, "box": [round(in_mm(c), 3) for c in b.GetBodyBox()],
                                           "flaechen": len(b.GetFaces() or ()), "check3": _fehlerzahl(b)})
    finally:
        sw.schliesse(app, model)
    return erg


def zusammenfassung(erg: dict, auswahl: set[int] | None = None) -> list[str]:
    z = []
    for k in erg["koerper"]:
        z.append(f"KÖRPER {k['nr']} {k['name']} box {k['box']} Flächen {k['flaechen']} {k['arten']} Check3 {k['check3']}")
        if auswahl is not None and k["nr"] not in auswahl:
            continue
        for c in k["zylinder"]:
            laenge = c["flaeche_mm2"] / (math.pi * c["durchmesser"]) if c["durchmesser"] else 0
            z.append(f"  Z Ø{c['durchmesser']:<7} ax={c['achspunkt']} r={c['richtung']} nahe={c['nahe']} "
                     f"n={c['flaechen']} A={c['flaeche_mm2']:.1f} L≈{laenge:.2f}")
        for s in k["sonstige"]:
            z.append(f"  S {s}")
        for e in k["ebenen"]:
            z.append(f"  E n={e['normale']} d={e['abstand']} nahe={e['nahe']} n={e['flaechen']} A={e['flaeche_mm2']:.1f}")
    for f in erg["flaechenkoerper"]:
        z.append(f"FLÄCHENKÖRPER {f['name']} box {f['box']} Flächen {f['flaechen']} Check3 {f['check3']}")
    return z


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("step", type=Path)
    a.add_argument("ausgabe", type=Path)
    a.add_argument("--koerper", help="Körpernummern für die Detailausgabe, z. B. 1,3")
    args = a.parse_args()
    erg = analysiere(args.step)
    args.ausgabe.write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    auswahl = {int(x) for x in args.koerper.split(",")} if args.koerper else None
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(zusammenfassung(erg, auswahl)))
    print("JSON:", args.ausgabe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
