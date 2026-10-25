"""S18: Exakte Zerlegung einer B-Rep in konvexe Teile für MuJoCo (jedes Netz kollidiert dort als seine konvexe Hülle).

Binäre Raumteilung (BSP) auf der B-Rep mit OCP-Splitter:
1. Schneidet die Ebene einer ebenen Fläche des Stücks das Stück selbst (Punkte des Stücks liegen außerhalb, also auf
   der Materialseite gegenüber), ist das Stück dort nicht konvex → an dieser Ebene teilen (größte solche Fläche zuerst).
2. Ohne solche Ebene bleiben gekrümmte Flächen: konvexe Zylinder (Verrundung außen) sind unschädlich; konkave Zylinder
   (Innenradius, Bohrung, Glassitz) werden an Ebenen durch die Achse geteilt, bis die Pfeilhöhe des Bogens je Stück
   ≤ toleranz ist – das ist der einzige Fehler der Zerlegung (die Hülle füllt die Pfeilhöhe).
Die Summe der Stückvolumen ist exakt das Volumen der B-Rep; geprüft wird zusätzlich der Füllfehler (Hüllvolumen −
Stückvolumen).

Längen in mm.
"""

import math
from dataclasses import dataclass

import numpy as np
from build123d import Keep, Plane, Solid, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cylinder
from scipy.spatial import ConvexHull

EPS_MM = 1e-6


@dataclass
class Stueck:
    punkte: np.ndarray       # Eckpunkte der Tessellierung (mm); MuJoCo bildet daraus die Hülle
    volumen: float
    huellvolumen: float


def _punkte(s: Solid, toleranz: float) -> np.ndarray:
    v, _ = s.tessellate(toleranz, 0.2)
    return np.array([(p.X, p.Y, p.Z) for p in v])


def _schneidende_ebene(s: Solid, pts: np.ndarray, toleranz: float):
    """Ebene einer ebenen Fläche, die das Stück schneidet, oder Teilungsebene eines konkaven Zylinders; None = konvex
    (innerhalb der Toleranz)."""
    beste, beste_flaeche = None, 0.0
    for f in s.faces():
        if f.geom_type.name != "PLANE":
            continue
        n = f.normal_at()
        c = f.center()
        d = (pts - np.array([c.X, c.Y, c.Z])) @ np.array([n.X, n.Y, n.Z])
        if d.max() > 1e-4 and f.area > beste_flaeche:
            beste, beste_flaeche = Plane(origin=c, z_dir=n), f.area
    if beste is not None:
        return beste
    for f in s.faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        zyl = ad.Cylinder()
        r = zyl.Radius()
        ax = zyl.Position()
        o, z, x, y = ax.Location(), ax.Direction(), ax.XDirection(), ax.YDirection()
        umin, umax, vmin, vmax = BRepTools.UVBounds_s(f.wrapped)
        um, vm = (umin + umax) / 2, (vmin + vmax) / 2
        radial = np.array([math.cos(um) * x.X() + math.sin(um) * y.X(), math.cos(um) * x.Y() + math.sin(um) * y.Y(),
                           math.cos(um) * x.Z() + math.sin(um) * y.Z()])
        p = np.array([o.X(), o.Y(), o.Z()]) + r * radial + vm * np.array([z.X(), z.Y(), z.Z()])
        n = f.normal_at(Vector(*p))
        konkav = float(np.dot([n.X, n.Y, n.Z], radial)) < 0     # Außennormale zeigt zur Achse
        if not konkav:
            continue
        spanne = umax - umin
        if r * (1 - math.cos(spanne / 2)) <= toleranz:
            continue
        zd = np.array([z.X(), z.Y(), z.Z()])
        normale = np.cross(zd, radial)
        return Plane(origin=Vector(o.X(), o.Y(), o.Z()), z_dir=Vector(*normale))
    return None


def _teile(ergebnis) -> list[Solid]:
    if ergebnis is None:
        return []
    if isinstance(ergebnis, (list, tuple)):
        return [s for e in ergebnis for s in _teile(e)]
    return list(ergebnis.solids())


def zerlege(solid: Solid, toleranz: float = 0.01, max_stuecke: int = 400) -> list[Stueck]:
    offen, fertig = [solid], []
    while offen:
        s = offen.pop()
        if s.volume < 1e-9:
            continue
        pts = _punkte(s, toleranz)
        ebene = _schneidende_ebene(s, pts, toleranz)
        if ebene is None:
            hv = ConvexHull(pts).volume
            fertig.append(Stueck(pts, s.volume, hv))
            continue
        teile = _teile(s.split(ebene, keep=Keep.BOTH))
        if len(teile) < 2:          # Ebene berührt nur (Rundung) – als konvex innerhalb der Toleranz annehmen
            fertig.append(Stueck(pts, s.volume, ConvexHull(pts).volume))
            continue
        offen.extend(teile)
        if len(offen) + len(fertig) > max_stuecke:
            raise RuntimeError(f"mehr als {max_stuecke} Stücke")
    return fertig


def bericht(solid: Solid, stuecke: list[Stueck]) -> dict:
    v = sum(s.volumen for s in stuecke)
    hv = sum(s.huellvolumen for s in stuecke)
    return dict(stuecke=len(stuecke), volumen_brep=round(solid.volume, 4), volumen_stuecke=round(v, 4),
                volumen_huellen=round(hv, 4), fuellfehler_mm3=round(hv - v, 4),
                fuellfehler_prozent=round(100 * (hv - v) / solid.volume, 5))
