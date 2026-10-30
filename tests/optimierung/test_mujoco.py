"""Prüfaufgabe mit echtem MuJoCo-Modell aus dem Schnellbau (MJCF = True, Spec C2 §3): ein Klotz auf der Rampe rutscht
oder haftet je nach Reibwert und Neigung."""

import copy

import pytest
import yaml

pytest.importorskip("mujoco")
pytest.importorskip("build123d")

from swki.optimierung.auftrag import lies_auftrag  # noqa: E402
from swki.optimierung.runner import Runner  # noqa: E402
from swki.spec.laden import lade_spec  # noqa: E402

from .beispiel import RAMPE, lege_an  # noqa: E402

KLOTZ = {"art": "teil", "name": "Klotz", "material": "1.0037", "parameter": {"A": 10},
         "features": [{"id": "f1", "typ": "extrusion",
                       "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=A",
                                                                                "hoehe": "=A"}}]},
                       "ende": {"typ": "blind", "tiefe": "=A"}}]}

AUFGABE = '''"""Klotz auf der Rampe (MuJoCo): rutscht er mindestens 5 mm hangabwärts?"""
import math
import mujoco
import numpy as np

MJCF = True
_modell = {}

def jobs(szenario, n, saat, erster=0):
    return [dict(szenario.get("werte", {}), nr=i) for i in range(erster, erster + n)]

def lauf(probe, job):
    key = id(probe)
    if key not in _modell:
        _modell.clear()
        _modell[key] = mujoco.MjModel.from_xml_string(probe["mjcf"])
    m = _modell[key]
    d = mujoco.MjData(m)
    m.geom_friction[:, 0] = job["mu"]
    p = probe["parameter"]["rampe.yaml"]
    # Klotz um die Hangneigung gedreht knapp über die Schräge legen (Lage aus den Parametern der Spec)
    a = math.atan2(p["H"], p["L"])
    x0 = 30.0 + 2.0 * job["nr"]
    y0 = p["H"] * (1 - x0 / p["L"])
    adr = m.joint("klotz").qposadr[0]
    mitte = np.array([x0 + 5 * math.sin(a), y0 + 5 * math.cos(a) + 0.05, p["B"] / 2]) * 1e-3
    d.qpos[adr:adr + 3] = mitte
    d.qpos[adr + 3:adr + 7] = [math.cos(-a / 2), 0, 0, math.sin(-a / 2)]
    start = mitte.copy()
    for _ in range(int(0.3 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    weg = float(np.linalg.norm(d.qpos[adr:adr + 3] - start)) * 1e3
    if weg > 5:
        return {"ergebnis": "richtig", "gueltig": True, "weg_mm": weg}
    return {"ergebnis": "liegt", "fehlerbild": "haftet", "gueltig": True, "weg_mm": weg}
'''


def test_klotz_rutscht_ab_genug_neigung(tmp_path):
    spec = copy.deepcopy(RAMPE)
    spec["optimierung"].update(
        pruefaufgabe={"modul": "aufgabe_rampe.py", "simulation": "rampe.sim.yaml"},
        stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 60]}], start=[{"H": 10.0}, {"H": 50.0}],
        szenarien=[{"name": "stahl", "laeufe": 4, "werte": {"mu": 0.3}}], budget={"proben": 2},
        pruefstufe2={"top_k": 0})
    pfad = lege_an(tmp_path / "auftrag", spec, AUFGABE)
    (pfad.parent / "klotz.yaml").write_text(yaml.safe_dump(KLOTZ), encoding="utf-8")
    sim = {"komponenten": {"rampe": {"material": "stahl"}}, "werkstoffe": {"stahl": {"mu": 0.3, "e": 0.3}},
           "werkstuecke": [{"id": "klotz", "spec": "klotz.yaml", "lage": [0, 200, 20], "material": "stahl"}],
           "zeitschritt_s": 1e-4, "kontakt_zeitkonstante_s": 2e-3}
    (pfad.parent / "rampe.sim.yaml").write_text(yaml.safe_dump(sim), encoding="utf-8")
    s = Runner(lies_auftrag(lade_spec(pfad), pfad), tmp_path / "arbeit" / "optimierung-1", kerne=2).starte()
    assert s["grund"] == "ZIEL", s["detail"]
    werte = {p["werte"]["H"]: p["wert"] for p in s["top"]}
    assert werte == {50.0: 1.0, 10.0: 0.0}            # tan 26,6° > 0,3 rutscht, tan 5,7° < 0,3 haftet
