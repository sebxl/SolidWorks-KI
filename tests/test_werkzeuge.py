"""Werkzeuge ohne SolidWorks: STL-Hüllquader; alle Werkzeug-Module importierbar."""

import importlib
import pkgutil
import struct

import pytest

import werkzeuge
from werkzeuge.stl_huellquader import beruehrt, huellquader

DREIECKE = [((0, 0, 0), (10, 0, 0), (0, 20, -5)), ((1, 1, 1), (2, 2, 30), (-3, 4, 5))]


def test_huellquader_binaer(tmp_path):
    d = bytearray(80) + struct.pack("<I", len(DREIECKE))
    for tri in DREIECKE:
        d += struct.pack("<3f", 0, 0, 1) + b"".join(struct.pack("<3f", *p) for p in tri) + b"\0\0"
    p = tmp_path / "teil.stl"
    p.write_bytes(bytes(d))
    assert huellquader(p) == ([-3, 0, -5], [10, 20, 30])


def test_huellquader_ascii(tmp_path):
    zeilen = ["solid teil"]
    for tri in DREIECKE:
        zeilen += ["facet normal 0 0 1", "outer loop"] + [f"vertex {x} {y} {z}" for x, y, z in tri] + ["endloop", "endfacet"]
    p = tmp_path / "teil.stl"
    p.write_text("\n".join(zeilen + ["endsolid teil"]), encoding="ascii")
    assert huellquader(p) == ([-3, 0, -5], [10, 20, 30])


def test_huellquader_leer(tmp_path):
    p = tmp_path / "leer.stl"
    p.write_text("solid leer\nendsolid leer\n", encoding="ascii")
    with pytest.raises(ValueError, match="keine Eckpunkte"):
        huellquader(p)


def test_beruehrt():
    lo, hi = [0, 0, 0], [10, 10, 10]
    assert beruehrt(lo, hi, [5, 20, -5, 5, 10, 11])
    assert not beruehrt(lo, hi, [11, 20, 0, 10, 0, 10])


@pytest.mark.parametrize("name", [m.name for m in pkgutil.iter_modules(werkzeuge.__path__)])
def test_werkzeug_importierbar(name):
    importlib.import_module(f"werkzeuge.{name}")
