"""Befehle "swki schnellbau teil <spec>" und "swki schnellbau mjcf <baugruppe> <sim.yaml> <aus.xml>" (Spec C1 §2).

Ohne SolidWorks; braucht das Extra `schnellbau`. Ausgabe JSON wie die übrigen Befehle; Fehler mit code und feature.
"""

import time
from pathlib import Path

import yaml

from swki.cli import SwkiFehler


def _module():
    try:
        from swki.schnellbau import baugruppe, mjcf, teil
    except ImportError as e:
        raise SwkiFehler(f"Extra 'schnellbau' fehlt ({e.name}): pip install -e .[schnellbau]") from e
    return teil, baugruppe, mjcf


def _setze(werte: list[str]) -> dict:
    out = {}
    for w in werte or []:
        name, sep, zahl = w.partition("=")
        if not sep:
            raise SwkiFehler(f"--setze erwartet NAME=wert (ist {w!r})")
        out[name] = float(zahl)
    return out


def exportiere_stl(solid, ziel: Path, toleranz_mm: float = 0.002) -> Path:
    """STL in Teilkoordinaten (mm), wie werkzeuge/messstand/stl_export.py es aus SolidWorks schreibt."""
    from build123d import export_stl
    ziel.parent.mkdir(parents=True, exist_ok=True)
    export_stl(solid, str(ziel), tolerance=toleranz_mm, angular_tolerance=0.05)
    return ziel


def _teil(args) -> dict:
    teil, _, _ = _module()
    t = teil.baue(Path(args.spec), _setze(args.setze), bohrungen=not args.ohne_bohrungen)
    bb = t.solid.bounding_box()
    erg = {"teil": t.name, "spec": args.spec, "volumen_mm3": round(t.solid.volume, 6),
           "huellquader_mm": [round(bb.size.X, 6), round(bb.size.Y, 6), round(bb.size.Z, 6)],
           "min_mm": [round(bb.min.X, 6), round(bb.min.Y, 6), round(bb.min.Z, 6)],
           "ms": round(t.sekunden * 1000, 1), "uebersprungen": t.uebersprungen}
    if args.stl:
        erg["stl"] = str(exportiere_stl(t.solid, Path(args.stl)))
    return erg


def _mjcf(args) -> dict:
    _, baugruppe, mjcf = _module()
    t0 = time.perf_counter()
    sim = yaml.safe_load(Path(args.sim).read_text(encoding="utf-8")) or {}
    bg = baugruppe.Baugruppe(Path(args.baugruppe), freigegeben=args.freigegeben)
    mod = mjcf.erzeuge(bg, sim, Path(args.baugruppe).parent)
    ziel = Path(args.aus)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(mod.xml, encoding="utf-8")
    return {"mjcf": str(ziel), "koerper": mod.koerper, "stuecke": mod.stuecke, "nicht_gebaut": bg.nicht_gebaut,
            "gelenke": [{"id": g.id, "typ": g.typ, "komponente": g.komponente, "eltern": g.eltern,
                         "achse": [round(float(c), 9) for c in g.achse], "bereich": g.bereich} for g in bg.gelenke],
            "meldungen": mod.meldungen, "s": round(time.perf_counter() - t0, 2)}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("schnellbau", help="Spec ohne SolidWorks bauen (OpenCascade) bzw. als MuJoCo-Modell")
    sub = p.add_subparsers(dest="schnellbau_befehl", required=True)
    t = sub.add_parser("teil", help="Teil-Spec bauen: Volumen, Hüllquader, Zeit; optional STL")
    t.add_argument("spec")
    t.add_argument("--setze", nargs="*", default=[], metavar="NAME=wert", help="Parameter überschreiben (mm/Grad)")
    t.add_argument("--stl", help="STL schreiben (Teilkoordinaten, mm)")
    t.add_argument("--ohne-bohrungen", action="store_true", help="Bohrungen weglassen (Kollisionsgeometrie)")
    t.set_defaults(func=_teil)
    m = sub.add_parser("mjcf", help="Baugruppe + Simulations-Datei → MJCF")
    m.add_argument("baugruppe")
    m.add_argument("sim", help="Simulations-Datei (YAML, siehe swki.schnellbau.mjcf)")
    m.add_argument("aus", help="Ziel .xml")
    m.add_argument("--freigegeben", action="store_true", help="die freigegebenen Kopien der Teil-Specs lesen")
    m.set_defaults(func=_mjcf)
