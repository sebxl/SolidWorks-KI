"""Exakte Zerlegung einer B-Rep in konvexe Stücke für MuJoCo, das jedes Netz als seine konvexe Hülle stoßen lässt
(Spec C1 §2; erprobt in Spike S-Schleife-1).

Raumteilung (BSP) mit dem OCP-Splitter:
1. Schneidet die Ebene einer ebenen Fläche das Stück (Punkte liegen auf ihrer Außenseite), ist es dort nicht konvex →
   an der größten solchen Ebene teilen.
2. Sonst bleiben konkave Zylinder (Innenradius, Bohrung, Sitz): an Ebenen durch die Achse teilen, bis die Pfeilhöhe
   des Bogens je Stück ≤ toleranz ist – der einzige Fehler der Zerlegung (die Hülle füllt die Pfeilhöhe).
Die Summe der Stückvolumen ist das Volumen der B-Rep; `bericht` nennt zusätzlich den Füllfehler (Hüllen − Stücke).
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

from swki.schnellbau.fehler import GEOMETRIE, SchnellbauFehler

AUSSEN_MM = 1e-4      # so weit dürfen Punkte eines Stücks über einer seiner Flächen liegen, ohne dass sie es teilt


@dataclass
class Stueck:
    punkte: np.ndarray       # Eckpunkte der Tessellierung (mm); MuJoCo bildet daraus die Hülle
    volumen: float
    huellvolumen: float


def _punkte(s: Solid, toleranz: float) -> np.ndarray:
    v, _ = s.tessellate(toleranz, 0.2)
    return np.array([(p.X, p.Y, p.Z) for p in v])


def _teilungsebene(s: Solid, pts: np.ndarray, toleranz: float) -> Plane | None:
    beste, groesste = None, 0.0
    for f in s.faces():
        if f.geom_type.name != "PLANE":
            continue
        n, c = f.normal_at(), f.center()
        d = (pts - np.array([c.X, c.Y, c.Z])) @ np.array([n.X, n.Y, n.Z])
        if d.max() > AUSSEN_MM and f.area > groesste:
            beste, groesste = Plane(origin=c, z_dir=n), f.area
    if beste is not None:
        return beste
    for f in s.faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        zyl = ad.Cylinder()
        r, ax = zyl.Radius(), zyl.Position()
        o, z, x, y = ax.Location(), ax.Direction(), ax.XDirection(), ax.YDirection()
        umin, umax, vmin, vmax = BRepTools.UVBounds_s(f.wrapped)
        um, vm = (umin + umax) / 2, (vmin + vmax) / 2
        radial = np.cos(um) * np.array([x.X(), x.Y(), x.Z()]) + np.sin(um) * np.array([y.X(), y.Y(), y.Z()])
        zd = np.array([z.X(), z.Y(), z.Z()])
        p = np.array([o.X(), o.Y(), o.Z()]) + r * radial + vm * zd
        n = f.normal_at(Vector(*p))
        konkav = float(np.dot([n.X, n.Y, n.Z], radial)) < 0     # Außennormale zeigt zur Achse
        if konkav and r * (1 - math.cos((umax - umin) / 2)) > toleranz:
            return Plane(origin=Vector(o.X(), o.Y(), o.Z()), z_dir=Vector(*np.cross(zd, radial)))
    return None


def _solids(ergebnis) -> list[Solid]:
    if ergebnis is None:
        return []
    if isinstance(ergebnis, (list, tuple)):
        return [s for e in ergebnis for s in _solids(e)]
    return list(ergebnis.solids())


def zerlege(solid: Solid, toleranz: float = 0.01, max_stuecke: int = 2000) -> list[Stueck]:
    offen, fertig = [solid], []
    while offen:
        s = offen.pop()
        if s.volume < 1e-9:
            continue
        pts = _punkte(s, toleranz)
        ebene = _teilungsebene(s, pts, toleranz)
        teile = _solids(s.split(ebene, keep=Keep.BOTH)) if ebene is not None else []
        if len(teile) < 2:          # konvex, oder die Ebene berührt nur (Rundung) – innerhalb der Toleranz
            fertig.append(Stueck(pts, s.volume, ConvexHull(pts).volume))
            continue
        offen.extend(teile)
        if len(offen) + len(fertig) > max_stuecke:
            raise SchnellbauFehler(GEOMETRIE, f"Zerlegung: mehr als {max_stuecke} Stücke (Toleranz {toleranz} mm)")
    return fertig


def bericht(solid: Solid, stuecke: list[Stueck]) -> dict:
    v = sum(s.volumen for s in stuecke)
    hv = sum(s.huellvolumen for s in stuecke)
    return dict(stuecke=len(stuecke), volumen_brep=round(solid.volume, 4), volumen_stuecke=round(v, 4),
                volumen_huellen=round(hv, 4), fuellfehler_mm3=round(hv - v, 4),
                fuellfehler_prozent=round(100 * (hv - v) / solid.volume, 5))
