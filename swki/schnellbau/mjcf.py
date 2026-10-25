"""Baugruppe + Simulations-Datei → MuJoCo-Modell (MJCF, Spec C1 §2).

Simulations-Datei (YAML, Bauweg wie `bezug`, nicht Teil der Freigabe):
  komponenten: {id: {material: schlüssel}}   stoßende Eigenteile (fehlt: alle gebauten, Werkstoff "standard")
  werkstoffe: {schlüssel: {mu: 0.35, e: 0.4, dichte: 7850}}   Reibwert, Stoßzahl, Dichte kg/m³
  werkstuecke: [{id, spec, lage: [x, y, z], material}]    freie Körper (Teil-Spec relativ zum Auftragsordner), mm
  zeitschritt_s (2e-5), kontakt_zeitkonstante_s (3e-4), schwerkraft ([0, -9.81, 0], Baugruppe y oben),
  zerlegung_toleranz_mm (0.01)
Körper nach dem Gelenkbaum der Baugruppe (Grundstellung, alle Körper bei pos 0, Geometrie in Baugruppenkoordinaten),
Gelenke mit ihrer ID als Namen. Geometrie der Komponenten: konvexe Stücke (swki.schnellbau.zerlegung); Mechanismus-
Körper stoßen nicht gegeneinander (contype 1, conaffinity 0), Werkstücke stoßen mit allem. Stoßzahl e → Dämpfung über
solref (Zeitkonstante, ζ = −ln e / √(π² + ln² e), wie die AP-6.8-Studien). Trägheit aus der B-Rep (GProp).
MJCF in Metern und Bogenmaß.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from build123d import Location
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

from swki.schnellbau.baugruppe import Baugruppe
from swki.schnellbau.teil import baue
from swki.schnellbau.zerlegung import zerlege

MM = 1e-3
STANDARD = {"mu": 0.35, "e": 0.4, "dichte": 7850.0}


def zeta(e: float) -> float:
    l = math.log(e)
    return -l / math.sqrt(math.pi ** 2 + l * l)


def masse(solid, dichte: float) -> tuple[float, np.ndarray, np.ndarray]:
    """(kg, Schwerpunkt m, Trägheitstensor kg·m² um den Schwerpunkt) eines Solid in mm."""
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid.wrapped, g)
    c = g.CentreOfMass()
    m = g.MatrixOfInertia()
    tensor = np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    return dichte * g.Mass() * 1e-9, np.array([c.X(), c.Y(), c.Z()]) * MM, dichte * tensor * 1e-15


def _summe(teile: list[tuple[float, np.ndarray, np.ndarray]]):
    m = sum(t[0] for t in teile)
    if m <= 0:
        return 0.0, np.zeros(3), np.zeros((3, 3))
    c = sum(t[0] * t[1] for t in teile) / m
    tensor = np.zeros((3, 3))
    for mi, ci, ii in teile:
        d = ci - c
        tensor += ii + mi * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return m, c, tensor


@dataclass
class Modell:
    xml: str
    koerper: dict = field(default_factory=dict)        # Körper → Komponenten
    stuecke: dict = field(default_factory=dict)        # Komponente/Werkstück → Anzahl Stücke
    meldungen: list = field(default_factory=list)


def _f(x) -> str:
    return " ".join(f"{float(c):.9g}" for c in x)


def erzeuge(bg: Baugruppe, sim: dict, ordner: Path | None = None) -> Modell:
    werkstoffe = {"standard": STANDARD, **{k: dict(STANDARD, **v) for k, v in sim.get("werkstoffe", {}).items()}}
    tol = sim.get("zerlegung_toleranz_mm", 0.01)
    tc = sim.get("kontakt_zeitkonstante_s", 3e-4)
    stoss = sim.get("komponenten") or {k: {"material": "standard"} for k in bg.komp}
    solids = bg.solids()
    assets, geoms, mod = [], {}, Modell("")

    def geometrie(name: str, solid, material: str, ziel: str, werkstueck: bool, ursprung=np.zeros(3)) -> None:
        """Stücke als Mesh-Geoms in den Körper ziel; ursprung (m): Rahmen des Körpers (Werkstück: Schwerpunkt)."""
        w = werkstoffe[material]
        ct, ca = (1, 1) if werkstueck else (1, 0)
        stuecke = zerlege(solid, tol)
        mod.stuecke[name] = len(stuecke)
        for i, s in enumerate(stuecke):
            assets.append(f'<mesh name="m_{name}_{i}" vertex="{_f((s.punkte * MM - ursprung).ravel())}"/>')
            geoms.setdefault(ziel, []).append(
                f'<geom name="{name}_{i}" type="mesh" mesh="m_{name}_{i}" contype="{ct}" conaffinity="{ca}" '
                f'friction="{w["mu"]} 0.005 0.0001" solref="{tc} {zeta(w["e"]):.6f}"/>')

    koerper_von = {kid: (k.koerper or "welt") for kid, k in bg.komp.items()}
    for kid, eintrag in stoss.items():
        if kid not in bg.komp:
            mod.meldungen.append(f"{kid}: nicht gebaut, ohne Geometrie")
            continue
        geometrie(kid, solids[kid], eintrag.get("material", "standard"), koerper_von[kid], False)
    for kid, k in bg.komp.items():
        mod.koerper.setdefault(koerper_von[kid], []).append(kid)

    def dichte(kid: str) -> float:
        return werkstoffe[stoss.get(kid, {}).get("material", "standard")]["dichte"]

    gelenke = {g.komponente: g for g in bg.gelenke}
    kinder = {}
    for g in bg.gelenke:
        kinder.setdefault(g.eltern or "welt", []).append(g.komponente)

    def koerper(name: str, tiefe: int) -> str:
        g = gelenke[name]
        m, c, tensor = _summe([masse(solids[k], dichte(k)) for k in mod.koerper.get(name, [])])
        if g.typ == "schub":
            gel = (f'<joint name="{g.id}" type="slide" axis="{_f(g.achse)}" range="{g.bereich[0] * MM:.9g} '
                   f'{g.bereich[1] * MM:.9g}" limited="true"/>')
        else:
            grenzen = "" if g.bereich is None else f' range="{g.bereich[0]:.9g} {g.bereich[1]:.9g}" limited="true"'
            gel = f'<joint name="{g.id}" type="hinge" pos="{_f(np.array(g.punkt) * MM)}" axis="{_f(g.achse)}"{grenzen}/>'
        tr = (f'<inertial pos="{_f(c)}" mass="{max(m, 1e-6):.9g}" fullinertia="{tensor[0, 0]:.9g} {tensor[1, 1]:.9g} '
              f'{tensor[2, 2]:.9g} {tensor[0, 1]:.9g} {tensor[0, 2]:.9g} {tensor[1, 2]:.9g}"/>') if m > 0 else \
            '<inertial pos="0 0 0" mass="1e-6" diaginertia="1e-12 1e-12 1e-12"/>'
        innen = "".join(koerper(k, tiefe + 1) for k in kinder.get(name, []))
        return f'<body name="{name}" pos="0 0 0">{gel}{tr}{"".join(geoms.get(name, []))}{innen}</body>'

    frei = []
    for w in sim.get("werkstuecke", []):
        teil = baue((ordner or bg.ordner) / w["spec"])
        lage = np.array([float(c) for c in w.get("lage", (0, 0, 0))])
        solid = teil.solid.moved(Location(tuple(lage)))
        m, c, tensor = masse(solid, werkstoffe[w.get("material", "standard")]["dichte"])
        # Rahmen im Schwerpunkt: das freie Gelenk dreht um den Körperrahmen (fern davon schaukelt der Körper auf)
        geometrie(w["id"], solid, w.get("material", "standard"), w["id"], True, c)
        frei.append(f'<body name="{w["id"]}" pos="{_f(c)}"><freejoint name="{w["id"]}"/>'
                    f'<inertial pos="0 0 0" mass="{m:.9g}" fullinertia="{tensor[0, 0]:.9g} {tensor[1, 1]:.9g} '
                    f'{tensor[2, 2]:.9g} {tensor[0, 1]:.9g} {tensor[0, 2]:.9g} {tensor[1, 2]:.9g}"/>'
                    f'{"".join(geoms.get(w["id"], []))}</body>')
    dt = sim.get("zeitschritt_s", 2e-5)
    g = sim.get("schwerkraft", [0, -9.81, 0])
    mod.xml = (f'<mujoco model="{bg.spec["name"]}"><compiler angle="radian"/>'
               f'<option timestep="{dt}" gravity="{_f(g)}" cone="elliptic" integrator="implicitfast">'
               f'<flag multiccd="enable"/></option><asset>{"".join(assets)}</asset>'
               f'<worldbody>{"".join(geoms.get("welt", []))}'
               f'{"".join(koerper(k, 1) for k in kinder.get("welt", []))}{"".join(frei)}</worldbody></mujoco>')
    mod.meldungen += bg.meldungen
    return mod
