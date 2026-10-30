"""MJCF aus der Baugruppe (Spec C1 §2, §4.1): kompiliert, Gelenke wie die Spec, Massen aus der B-Rep, ein Werkstück
fällt auf die Grundplatte und bleibt dort liegen."""

import math
from pathlib import Path

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")
pytest.importorskip("build123d")

from swki.schnellbau.baugruppe import Baugruppe  # noqa: E402
from swki.schnellbau.mjcf import erzeuge, masse  # noqa: E402

REFERENZ = Path(__file__).parents[1] / "referenz"


@pytest.fixture(scope="module")
def schlitten():
    return Baugruppe(REFERENZ / "schlitten" / "linearschlitten.yaml")


def test_linearschlitten_kompiliert_mit_gelenkbaum(schlitten):
    mod = erzeuge(schlitten, {"zerlegung_toleranz_mm": 0.05})
    m = mujoco.MjModel.from_xml_string(mod.xml)
    g1, s1 = m.joint("g1"), m.joint("s1")
    assert g1.type[0] == mujoco.mjtJoint.mjJNT_SLIDE and s1.type[0] == mujoco.mjtJoint.mjJNT_HINGE
    assert g1.range == pytest.approx([0, 0.220])
    assert s1.range == pytest.approx([0, math.pi / 2])
    assert m.body("hebel").parentid[0] == m.body("schlitten").id
    assert m.body("schlitten").parentid[0] == 0
    assert m.jnt_axis[s1.id] == pytest.approx([0, -1, 0])
    # Masse des Schlittenkörpers = Dichte × Volumen der B-Rep (Stahl 7850)
    v = schlitten.komp["schlitten"].teil.solid.volume
    assert m.body("schlitten").mass[0] == pytest.approx(7850 * v * 1e-9, rel=1e-6)


def test_masse_und_traegheit_eines_quaders():
    from build123d import Box
    m, c, tensor = masse(Box(100, 20, 10), 1000)
    assert m == pytest.approx(1000 * 20000e-9)
    assert c == pytest.approx([0, 0, 0], abs=1e-12)
    assert tensor[0, 0] == pytest.approx(m * (0.02 ** 2 + 0.01 ** 2) / 12)


def test_werkstueck_faellt_auf_die_grundplatte(schlitten, tmp_path):
    klotz = tmp_path / "klotz.yaml"
    klotz.write_text("art: teil\nname: Klotz\nmaterial: Stahl\nparameter: {}\nfeatures:\n"
                     "  - {id: f1, typ: extrusion, skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], "
                     "breite: 10, hoehe: 10}}]}, ende: {typ: blind, tiefe: 10}}\n", encoding="utf-8")
    sim = {"komponenten": {"grundplatte": {"material": "stahl"}}, "werkstoffe": {"stahl": {"mu": 0.5, "e": 0.3}},
           "werkstuecke": [{"id": "klotz", "spec": klotz.name, "lage": [100, 40, 0], "material": "stahl"}]}
    mod = erzeuge(schlitten, sim, tmp_path)
    m = mujoco.MjModel.from_xml_string(mod.xml)
    d = mujoco.MjData(m)
    for _ in range(int(0.5 / m.opt.timestep)):
        mujoco.mj_step(m, d)
    k, j = m.body("klotz").id, m.joint("klotz")
    unten = d.xipos[k][1] - 0.005                         # Unterseite des 10-mm-Klotzes
    assert unten == pytest.approx(0.020, abs=5e-4)        # Grundplatte oben y 20 (Eindringung < 0,5 mm)
    assert d.xipos[k][[0, 2]] == pytest.approx([0.1, 0.0], abs=1e-5)       # nicht verrutscht
    assert np.abs(d.qvel[j.dofadr[0]:j.dofadr[0] + 6]).max() < 1e-4
    assert abs(d.xmat[k].reshape(3, 3)[1, 1]) == pytest.approx(1, abs=1e-6)   # liegt flach
