"""Vergleich Ergebnis-STL gegen Referenz-STL (Spec Messstand §3) mit synthetischen Netzen, ohne SolidWorks."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

from werkzeuge.messstand.vergleich import SICHER_MM, Oberflaeche, naechster_punkt_dreieck, stuetzstellen, vergleiche

WURZEL = Path(__file__).resolve().parents[2]


# --- synthetische Teile (ohne Boolesche Operationen: manifold3d ist nicht installiert) ---


def platte_mit_bohrung(a: float, b: float, h: float, mitte, r: float, n: int = 128) -> trimesh.Trimesh:
    """Quader [0,a]×[0,b]×[0,h] mit Durchgangsbohrung (Radius r, Achse z) bei mitte = (x, y)."""
    hx, hy = mitte
    ecken = [np.arctan2(y - hy, x - hx) for x, y in ((0, 0), (a, 0), (a, b), (0, b))]
    winkel = np.unique(np.mod(np.concatenate([np.linspace(0, 2 * np.pi, n, endpoint=False), ecken]), 2 * np.pi))
    c, s = np.cos(winkel), np.sin(winkel)
    innen = np.column_stack([hx + r * c, hy + r * s])
    with np.errstate(divide="ignore"):
        t = np.min(np.where(np.column_stack([c > 0, c < 0, s > 0, s < 0]),
                            np.column_stack([(a - hx) / c, -hx / c, (b - hy) / s, -hy / s]), np.inf), axis=1)
    aussen = np.column_stack([hx + t * c, hy + t * s])
    m = len(winkel)
    i = np.arange(m)
    j = (i + 1) % m
    dreiecke = np.vstack([np.column_stack([i, m + i, m + j]), np.column_stack([i, m + j, j])])
    return trimesh.creation.extrude_triangulation(np.vstack([innen, aussen]), dreiecke, h)


def quader(a: float, b: float, h: float, ursprung=(0, 0, 0)) -> trimesh.Trimesh:
    """Achsparalleler Quader mit Ecke im ursprung."""
    q = trimesh.creation.box(extents=[a, b, h])
    q.apply_translation(np.array([a, b, h]) / 2 + np.array(ursprung, dtype=float))
    return q


def stecker(zapfen_x: float = 30.0) -> trimesh.Trimesh:
    """Grundkörper 40×20×10 mit Zapfen 6×6×8 auf der +y-Fläche, außermittig in x (Mitte zapfen_x) und z (Mitte 4)."""
    return trimesh.util.concatenate([quader(40, 20, 10), quader(6, 8, 6, (zapfen_x - 3, 20, 1))])


def speichere(netz: trimesh.Trimesh, pfad: Path) -> Path:
    netz.export(pfad)
    return pfad


def bewegt(netz: trimesh.Trimesh, winkel: float, achse, verschiebung) -> trimesh.Trimesh:
    n = netz.copy()
    n.apply_transform(trimesh.transformations.rotation_matrix(winkel, achse))
    n.apply_translation(verschiebung)
    return n


# --- exakter Punkt-zu-Dreieck-Abstand ---


def test_naechster_punkt_dreieck_alle_bereiche():
    a, b, c = np.array([0.0, 0, 0]), np.array([1.0, 0, 0]), np.array([0.0, 1, 0])
    faelle = {  # Punkt -> nächster Punkt auf dem Dreieck
        (0.2, 0.2, 3): (0.2, 0.2, 0),     # Fläche
        (-1, -1, 0): (0, 0, 0),           # Ecke a
        (2, -1, 1): (1, 0, 0),            # Ecke b
        (-1, 2, 0): (0, 1, 0),            # Ecke c
        (0.5, -2, 0): (0.5, 0, 0),        # Kante ab
        (-2, 0.5, 0): (0, 0.5, 0),        # Kante ac
        (1, 1, 0): (0.5, 0.5, 0),         # Kante bc
    }
    p = np.array(list(faelle), dtype=float)
    q = naechster_punkt_dreieck(p, np.tile(a, (len(p), 1)), np.tile(b, (len(p), 1)), np.tile(c, (len(p), 1)))
    np.testing.assert_allclose(q, np.array(list(faelle.values()), dtype=float), atol=1e-12)


def test_stuetzstellen_decken_jedes_dreieck_ab():
    """Jeder Dreieckspunkt liegt höchstens radius von einer Stützstelle desselben Dreiecks (auch spitz, rechtwinklig)."""
    dreiecke = np.array([
        [[0, 0, 0], [10, 0, 0], [3, 7, 0]],          # breit
        [[0, 0, 0], [30, 0.01, 0], [30, 0, 0.02]],   # Nadel
        [[0, 0, 0], [5, 0, 0], [0, 4, 0]],           # rechter Winkel an der Ecke (Fußpunkt am Kantenende)
        [[1, 2, 3], [1.5, 2.2, 3.1], [1.2, 2.8, 2.9]],  # kleiner als ein Rasterschritt
    ], dtype=float)
    mitten, wer, radius = stuetzstellen(dreiecke, 0.5)
    assert radius <= 0.5 / np.sqrt(2) + 1e-12
    rng = np.random.default_rng(2)
    for i, t in enumerate(dreiecke):
        r1, r2 = np.sqrt(rng.random(2000)), rng.random(2000)
        x = (1 - r1)[:, None] * t[0] + (r1 * (1 - r2))[:, None] * t[1] + (r1 * r2)[:, None] * t[2]
        x = np.vstack([x, t])
        eigene = mitten[wer == i]
        naechste = np.linalg.norm(x[:, None] - eigene[None], axis=2).min(axis=1)
        assert naechste.max() <= radius + 1e-9
    assert (wer == 0).sum() < 0.75 * np.ceil(10 / 0.5) * np.ceil(7 / 0.5)  # Zellen außerhalb des Dreiecks fallen weg


def test_oberflaeche_abstand_exakt_wie_alle_dreiecke():
    """Kandidatensuche über den KD-Baum: bis SICHER_MM exakt wie die Prüfung aller Dreiecke, darüber sicher ≥ SICHER_MM."""
    netz = platte_mit_bohrung(40, 30, 20, (12, 10), 2, n=64)
    o = Oberflaeche(netz.triangles)
    rng = np.random.default_rng(1)
    p = np.vstack([rng.uniform([-10, -10, -10], [50, 40, 30], size=(400, 3)),
                   netz.sample(400, seed=3) + rng.normal(scale=0.3, size=(400, 3))])  # viele nahe der Oberfläche
    d, _ = o.abstand(p)
    voll = np.min([np.linalg.norm(p - naechster_punkt_dreieck(p, *[np.tile(e, (len(p), 1)) for e in t]), axis=1)
                   for t in netz.triangles], axis=0)
    nah = voll <= SICHER_MM
    assert nah.sum() > 300
    np.testing.assert_allclose(d[nah], voll[nah], atol=1e-9)
    assert np.all(d[~nah] >= SICHER_MM) and np.all(d >= voll - 1e-9)


def test_oberflaeche_abstand_quader_analytisch():
    o = Oberflaeche(trimesh.creation.box(extents=[10, 10, 10]).triangles)
    d, q = o.abstand(np.array([[20.0, 0, 0], [0, 0, 0], [8, 8, 0]]))
    np.testing.assert_allclose(d, [15, 5, np.sqrt(18)], atol=1e-12)
    np.testing.assert_allclose(q[0], [5, 0, 0], atol=1e-12)


# --- Vergleich ---


def test_identischer_quader_mit_bohrung(tmp_path):
    teil = platte_mit_bohrung(40, 30, 20, (12, 10), 3)
    e = speichere(teil, tmp_path / "e.stl")
    r = speichere(teil, tmp_path / "r.stl")
    erg = vergleiche(e, r)
    assert erg["richtig"] is True
    assert erg["gespiegelt"] is False
    b = erg["beste"]
    assert b["eigentlich"] is True
    assert b["p99_mm"] < 1e-6 and b["max_mm"] < 1e-6
    assert b["volumen_abw_prozent"] < 1e-6 and b["huelle_abw_mm"] < 1e-6
    assert b["volumen_referenz"] == pytest.approx(40 * 30 * 20 - np.pi * 9 * 20, rel=2e-3)
    np.testing.assert_allclose(b["matrix"], np.eye(3))
    json.dumps(erg)  # JSON-serialisierbar
    for teil_erg in (erg["beste"], erg["beste_eigentlich"], erg["beste_uneigentlich"]):
        for k in ("p99_mm", "max_mm", "mittel_mm", "volumen_ergebnis", "volumen_referenz", "volumen_abw_prozent",
                  "huelle_ergebnis", "huelle_referenz", "huelle_abw_mm", "matrix", "eigentlich"):
            assert k in teil_erg
    assert erg["beste_uneigentlich"]["eigentlich"] is False


def test_verschoben_und_gedreht_ist_richtig(tmp_path):
    teil = platte_mit_bohrung(40, 30, 20, (12, 10), 3)
    e = speichere(bewegt(teil, np.pi / 2, [0, 0, 1], [100, -50, 7]), tmp_path / "e.stl")
    r = speichere(teil, tmp_path / "r.stl")
    erg = vergleiche(e, r)
    assert erg["richtig"] is True
    assert erg["beste"]["p99_mm"] < 1e-3
    assert np.linalg.det(np.array(erg["beste"]["matrix"])) == pytest.approx(1)


def test_gespiegelter_stecker(tmp_path):
    spiegel = stecker()
    spiegel.apply_transform(np.diag([-1.0, 1, 1, 1]))  # an der YZ-Ebene
    assert spiegel.volume > 0
    e = speichere(spiegel, tmp_path / "e.stl")
    r = speichere(stecker(), tmp_path / "r.stl")
    erg = vergleiche(e, r)
    assert erg["richtig"] is False
    assert erg["gespiegelt"] is True
    assert erg["beste"]["eigentlich"] is False
    assert erg["beste_uneigentlich"]["p99_mm"] < 1e-3
    assert erg["beste_eigentlich"]["p99_mm"] > 0.3


def test_zapfen_versetzt(tmp_path):
    e = speichere(stecker(33.0), tmp_path / "e.stl")
    r = speichere(stecker(30.0), tmp_path / "r.stl")
    erg = vergleiche(e, r)
    assert erg["richtig"] is False
    assert erg["gespiegelt"] is False
    assert erg["beste"]["volumen_abw_prozent"] < 1e-6  # nur die Lage des Zapfens ist falsch


def test_bohrung_fehlt_greift_ueber_p99(tmp_path):
    """Bohrung Ø4 in einem Würfel 60: Volumen weicht < 0,5 % ab, Hülle gleich – erst p99 erkennt den Fehler."""
    e = speichere(quader(60, 60, 60), tmp_path / "e.stl")
    r = speichere(platte_mit_bohrung(60, 60, 60, (25, 35), 2), tmp_path / "r.stl")
    erg = vergleiche(e, r)
    b = erg["beste"]
    assert b["volumen_abw_prozent"] < 0.5
    assert b["huelle_abw_mm"] <= 0.3
    assert b["p99_mm"] > 0.3
    assert erg["richtig"] is False
    assert erg["gespiegelt"] is False


def test_zylinder_fein_gedreht(tmp_path):
    zyl = trimesh.creation.cylinder(radius=10, height=30, sections=256)
    anders = bewegt(zyl, np.pi / 256, [0, 0, 1], [0, 0, 0])  # Tesselierung um eine halbe Teilung versetzt
    anders = bewegt(anders, np.pi / 2, [1, 0, 0], [5, 6, -7])
    e = speichere(anders, tmp_path / "e.stl")
    r = speichere(zyl, tmp_path / "r.stl")
    erg = vergleiche(e, r)
    assert erg["richtig"] is True
    assert erg["beste"]["p99_mm"] < 0.05


def test_gleiche_saat_gleiches_ergebnis(tmp_path):
    e = speichere(stecker(33.0), tmp_path / "e.stl")
    r = speichere(stecker(30.0), tmp_path / "r.stl")
    assert vergleiche(e, r, punkte=5000, saat=3) == vergleiche(e, r, punkte=5000, saat=3)


def test_aufruf_ueber_kommandozeile(tmp_path):
    teil = platte_mit_bohrung(40, 30, 20, (12, 10), 3)
    e = speichere(teil, tmp_path / "e.stl")
    r = speichere(teil, tmp_path / "r.stl")
    aus = subprocess.run([sys.executable, "-m", "werkzeuge.messstand.vergleich", str(e), str(r)],
                         cwd=WURZEL, capture_output=True, text=True, encoding="utf-8", check=True)
    assert json.loads(aus.stdout)["richtig"] is True
