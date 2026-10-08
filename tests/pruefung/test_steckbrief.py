import json
import math
import time

import pytest

np = pytest.importorskip("numpy")
trimesh = pytest.importorskip("trimesh")
pytest.importorskip("scipy")

from swki.pruefung.steckbrief import als_text, steckbrief  # noqa: E402

QUADER = (75.0, 29.9, 89.0)  # Hüllquader X −37,5…37,5  Y 0…29,9  Z −44,5…44,5


def _quader(extents=QUADER, mitte=(0.0, 14.95, 0.0)):
    return trimesh.creation.box(extents=extents, transform=trimesh.transformations.translation_matrix(mitte))


def _zylinder_z(x, y, z0, z1, d, sections=64, drehung=0.0):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    if drehung:
        m.apply_transform(trimesh.transformations.rotation_matrix(drehung, (0, 0, 1)))
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def _prisma(umriss, z0, z1):
    """Geschlossenes Prisma aus konvexem Umriss (gegen den Uhrzeigersinn) in XY, Höhe Z."""
    n = len(umriss)
    unten = [(x, y, z0) for x, y in umriss]
    oben = [(x, y, z1) for x, y in umriss]
    cx, cy = np.mean(umriss, axis=0)
    v = unten + oben + [(cx, cy, z0), (cx, cy, z1)]
    mu, mo = 2 * n, 2 * n + 1
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i), (mu, j, i), (mo, n + i, n + j)]
    return trimesh.Trimesh(vertices=v, faces=f, process=True)


def _langloch_umriss(x0, x1, r, k=32):
    """Stadion entlang X: Halbkreise um (x1,0) und (x0,0), gegen den Uhrzeigersinn."""
    p = [(x1 + r * math.cos(t), r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, k + 1)]
    p += [(x0 + r * math.cos(t), r * math.sin(t)) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, k + 1)]
    return p


def _sb(tmp_path, mesh, name="teil.stl"):
    pfad = tmp_path / name
    mesh.export(pfad)
    return steckbrief(pfad)


def _zyl(sb, achse, art):
    return [z for z in sb["zylinder"] if z["achse"] == achse and z["art"] == art]


def test_quader_mit_zapfen(tmp_path):
    m = trimesh.util.concatenate([_quader(), _zylinder_z(-12.5, 15.6, -44.5, -28.5, 12)])
    sb = _sb(tmp_path, m)
    assert sb["huellquader"]["min"] == pytest.approx([-37.5, 0, -44.5], abs=1e-3)
    assert sb["huellquader"]["kanten"] == pytest.approx([75, 29.9, 89], abs=1e-3)
    assert sb["koerper"] == 2
    (z,) = sb["zylinder"]
    assert z["achse"] == "Z" and z["art"] == "aussen"
    assert z["durchmesser"] == pytest.approx(12, abs=0.05)
    assert z["mitte"]["x"] == pytest.approx(-12.5, abs=0.05)
    assert z["mitte"]["y"] == pytest.approx(15.6, abs=0.05)
    assert set(z["mitte"]) == {"x", "y"}
    assert (z["von"], z["bis"]) == pytest.approx((-44.5, -28.5), abs=0.01)
    assert z["winkel_grad"] == pytest.approx(360, abs=0.5)
    assert z["beruehrt"] == ["-Z"]
    assert sb["seiten"]["-Z"]["koordinate"] == pytest.approx(-44.5, abs=1e-3)
    assert sb["seiten"]["-Z"]["zylinder"] == [0]
    assert sb["seiten"]["+Z"]["zylinder"] == []
    json.dumps(sb)


def test_achsparallele_facetten_stoeren_nicht(tmp_path):
    # Facetten mit Normale ∥ X/Y sind keine Kandidaten – der Zylinder zerfällt in Bögen, die wieder vereint werden.
    m = _zylinder_z(3, -4, 0, 10, 20, sections=48, drehung=math.pi / 48)
    (z,) = _sb(tmp_path, m)["zylinder"]
    assert z["durchmesser"] == pytest.approx(20, abs=0.05)
    assert z["winkel_grad"] == pytest.approx(360, abs=0.5)


def test_gespiegelt_unterscheidet_sich_im_text(tmp_path):
    links = als_text(_sb(tmp_path, trimesh.util.concatenate([_quader(), _zylinder_z(-12.5, 15.6, -44.5, -28.5, 12)]), "a.stl"))
    rechts = als_text(_sb(tmp_path, trimesh.util.concatenate([_quader(), _zylinder_z(12.5, 15.6, -44.5, -28.5, 12)]), "b.stl"))
    assert links != rechts
    assert "x −12,5" in links and "x 12,5" in rechts
    zeile = next(z for z in links.splitlines() if "Ø12" in z)
    assert "Achse Z" in zeile and "außen" in zeile and "berührt −Z" in zeile


def test_rohr_achse_y(tmp_path):
    m = trimesh.creation.annulus(r_min=8, r_max=12.7, height=30, sections=64)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
    m.apply_translation((5, 0, -7))
    sb = _sb(tmp_path, m)
    (a,) = _zyl(sb, "Y", "aussen")
    (i,) = _zyl(sb, "Y", "innen")
    assert len(sb["zylinder"]) == 2
    assert a["durchmesser"] == pytest.approx(25.4, abs=0.05)
    assert i["durchmesser"] == pytest.approx(16, abs=0.05)
    assert i["mitte"] == pytest.approx({"x": 5, "z": -7}, abs=0.05)
    assert (i["von"], i["bis"]) == pytest.approx((-15, 15), abs=0.01)
    assert sorted(a["beruehrt"]) == ["+Y", "-Y"]
    assert i["beruehrt"] == []
    text = als_text(sb)
    assert "Bohrung Ø16" in text and "Zylinder außen Ø25,4" in text


def test_langloch_halbzylinder(tmp_path):
    zapfen = _prisma(_langloch_umriss(-5, 5, 2.4), 0, 2)
    sb = _sb(tmp_path, zapfen)
    z = _zyl(sb, "Z", "aussen")
    assert len(z) == 2
    assert sorted(round(k["mitte"]["x"], 2) for k in z) == [-5, 5]
    for k in z:
        assert k["durchmesser"] == pytest.approx(4.8, abs=0.05)
        assert k["winkel_grad"] == pytest.approx(180, abs=1)

    loch = zapfen.copy()
    loch.invert()
    sb = _sb(tmp_path, loch, "loch.stl")
    assert len(_zyl(sb, "Z", "innen")) == 2
    assert "Bogen 180°" in als_text(sb)


def test_zwei_quader_zwei_koerper(tmp_path):
    m = trimesh.util.concatenate([_quader((10, 10, 10), (0, 0, 0)), _quader((10, 10, 10), (30, 0, 0))])
    sb = _sb(tmp_path, m)
    assert sb["koerper"] == 2
    assert sb["volumen_mm3"] == pytest.approx(2000, rel=1e-6)
    assert sb["schwerpunkt"] == pytest.approx([15, 0, 0], abs=1e-6)


def test_quader_allein(tmp_path):
    sb = _sb(tmp_path, _quader())
    assert sb["zylinder"] == []
    assert sb["koerper"] == 1
    assert sb["volumen_mm3"] == pytest.approx(75 * 29.9 * 89, rel=1e-6)
    assert sb["flaeche_mm2"] == pytest.approx(2 * (75 * 29.9 + 75 * 89 + 29.9 * 89), rel=1e-6)
    text = als_text(sb)
    zeilen = text.splitlines()
    assert zeilen[0] == "Hüllquader X −37,5…37,5  Y 0…29,9  Z −44,5…44,5  (75 × 29,9 × 89)"
    assert "Körper 1" in zeilen[1] and "Volumen 199582,5 mm³" in zeilen[1]


def test_schraege_wand_ist_kein_zylinder(tmp_path):
    # Senkrechte, schräge Ebenen (Normale ⊥ Z, nicht ∥ X/Y) dürfen nicht als Zylinder gelten.
    m = _prisma([(0, 0), (40, 0), (55, 30), (-10, 30)], 0, 10)
    m = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 3.0))
    assert _sb(tmp_path, m)["zylinder"] == []


def test_text_hoechstens_40_zeilen(tmp_path):
    teile = [_quader((200, 10, 200), (0, -5, 0))]
    teile += [_zylinder_z(-90 + 9 * i, 3, 0, 4 + (i % 3), 3 + 0.5 * i, sections=24) for i in range(60)]
    text = als_text(_sb(tmp_path, trimesh.util.concatenate(teile)))
    assert len(text.splitlines()) <= 40


def test_laufzeit_50k_dreiecke(tmp_path):
    teile = [trimesh.creation.icosphere(subdivisions=5, radius=20)]  # 20480 Dreiecke
    teile += [_zylinder_z(30 + 10 * (i % 6), 10 * (i // 6), 0, 20, 6, sections=128) for i in range(58)]
    m = trimesh.util.concatenate(teile)
    assert len(m.faces) > 49000
    pfad = tmp_path / "gross.stl"
    m.export(pfad)
    t0 = time.perf_counter()
    sb = steckbrief(pfad)
    als_text(sb)
    assert time.perf_counter() - t0 < 3.0
    assert len(_zyl(sb, "Z", "aussen")) == 58
