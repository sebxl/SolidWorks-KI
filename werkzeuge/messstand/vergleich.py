"""Ergebnis-STL gegen Referenz-STL vergleichen, unabhängig von Lage und Achsenrichtung; Spiegelung wird erkannt.

Spec docs/superpowers/specs/2026-10-09-messstand-design.md §3. Ohne SolidWorks; braucht numpy, scipy, trimesh
(kein rtree/embree: der exakte Punkt-zu-Dreieck-Abstand ist hier selbst geschrieben).

Je Achsenmatrix (24 eigentliche, 24 uneigentliche) wird das Ergebnis gedreht, die Schwerpunkte werden
übereinandergelegt, dann zählt der beidseitige Oberflächenabstand (Punktstichprobe → nächster Punkt der anderen
Oberfläche). Grob mit wenigen Punkten für alle 48, fein für die besten je Art. p99, max, mittel über beide
Richtungen zusammen.

Keine Feinjustierung der Verschiebung (ICP) nach dem Schwerpunkt: gemessen ohne Nutzen bei richtigen Teilen
(Zylinder 64 gegen 256 Teilungen: Verschiebung 0), aber nachsichtiger bei falschen (fehlende Bohrung am Stabende:
p99 0,27 → 0,23 mm).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.messstand.vergleich <ergebnis.stl> <referenz.stl> [--punkte N] [--saat S]
Ausgabe JSON (mm wie in den Dateien).
"""

import argparse
import itertools
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

GRENZE_VOLUMEN_PROZENT = 0.5
GRENZE_HUELLE_MM = 0.3
GRENZE_P99_MM = 0.3
GRENZE_MAX_MM = 1.0       # kleine fehlende Merkmale (Bohrung) fallen in p99 nicht auf

GROB_PUNKTE = 3000      # Punkte je Netz für die Bewertung aller 48 Matrizen
FEIN_JE_ART = 2         # so viele beste eigentliche und uneigentliche Matrizen werden fein gemessen
K_STUFEN = (8, 32, 128)  # Kandidaten-Stützstellen je Punkt; die nächste Stufe nur für nicht belegte Punkte
RASTER = 200            # Stützstellen-Raster: Zellen ≤ Diagonale/RASTER …
MAX_STUETZSTELLEN = 2_000_000  # … höchstens so viele, sonst gröber
SICHER_MM = 1.0         # Abstände bis hier exakt belegt; darüber nur belegt, dass sie ≥ SICHER_MM sind
BLOCK = 2048            # Punkte je Rechenblock (Speicher)
GROB_EPS = 1.0          # Grobphase: genäherte Nachbarsuche (KD-Baum eps), Feinphase immer exakt
FAEDEN = 8              # parallele Rechenblöcke (Speicher: je Faden einige 100 MB bei dichten Netzen)


def achsenmatrizen() -> list[np.ndarray]:
    """Alle 48 Achsenmatrizen (Permutation × Vorzeichen), Einheitsmatrix zuerst."""
    matrizen = []
    for perm in itertools.permutations(range(3)):
        for vorzeichen in itertools.product((1.0, -1.0), repeat=3):
            m = np.zeros((3, 3))
            m[np.arange(3), perm] = vorzeichen
            matrizen.append(m)
    return matrizen


def _punkt(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.einsum("ij,ij->i", x, y)


def naechster_punkt_dreieck(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Nächster Punkt auf den Dreiecken (a, b, c) zu den Punkten p, zeilenweise (Ericson, Real-Time Collision Detection)."""
    ab, ac = b - a, c - a
    d1, d2 = _punkt(ab, p - a), _punkt(ac, p - a)
    d3, d4 = _punkt(ab, p - b), _punkt(ac, p - b)
    d5, d6 = _punkt(ab, p - c), _punkt(ac, p - c)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        nenner = va + vb + vc
        q = a + ab * (vb / nenner)[:, None] + ac * (vc / nenner)[:, None]                  # innen
        # Bereiche in umgekehrter Vorrang-Reihenfolge, spätere überschreiben frühere
        m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)                                     # Kante bc
        q = np.where(m[:, None], b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None], q)
        m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)                                               # Kante ac
        q = np.where(m[:, None], a + ac * (d2 / (d2 - d6))[:, None], q)
        q = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, q)                               # Ecke c
        m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)                                               # Kante ab
        q = np.where(m[:, None], a + ab * (d1 / (d1 - d3))[:, None], q)
        q = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, q)                               # Ecke b
        q = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, q)                                # Ecke a
    return q


def _raster(t: np.ndarray, schritt: float) -> tuple:
    """Je Dreieck: längste Kante a→b, Gegenecke c, Rechteck über ab bis zur Höhe von c, Zellenzahl je Richtung."""
    kanten = np.linalg.norm(t[:, [1, 2, 0]] - t, axis=2)                # Kante i: Ecke i → Ecke i+1
    r = np.arange(len(t))
    i = kanten.argmax(axis=1)
    a, b, c = t[r, i], t[r, (i + 1) % 3], t[r, (i + 2) % 3]
    laenge = kanten[r, i]
    u = (b - a) / laenge[:, None]
    tc = _punkt(c - a, u)                                               # Fußpunkt von c, liegt in [0, laenge]
    senk = c - a - tc[:, None] * u
    hoehe = np.linalg.norm(senk, axis=1)
    v = senk / hoehe[:, None]
    nu = np.maximum(np.ceil(laenge / schritt), 1).astype(np.int64)
    nv = np.maximum(np.ceil(hoehe / schritt), 1).astype(np.int64)
    return a, u, v, laenge, tc, hoehe, nu, nv


def stuetzstellen(dreiecke: np.ndarray, schritt: float) -> tuple[np.ndarray, np.ndarray, float]:
    """(Zellmitten, Dreieck je Zellmitte, größter Abstand Dreieckspunkt → Zellmitte desselben Dreiecks).

    Raster im Rechteck über der längsten Kante, nur Zellen, die das Dreieck berühren; jeder Punkt eines Dreiecks
    liegt in einer seiner Zellen, also höchstens eine halbe Zellendiagonale von deren Mitte. Anzahl wächst bei
    spitzen Dreiecken linear mit der Länge, sonst mit der Fläche.
    """
    a, u, v, laenge, tc, hoehe, nu, nv = _raster(dreiecke, schritt)
    du, dv = laenge / nu, hoehe / nv
    anzahl = nu * nv
    wer = np.repeat(np.arange(len(dreiecke)), anzahl)
    lokal = np.arange(anzahl.sum()) - np.repeat(np.cumsum(anzahl) - anzahl, anzahl)
    iu, iv = lokal // nv[wer], lokal % nv[wer]
    x0, y0 = iu * du[wer], iv * dv[wer]
    # höchster Punkt des Dreiecks über [x0, x0 + du] (Zelt mit Spitze bei tc, Höhe hoehe)
    tcw, lw, hw = tc[wer], laenge[wer], hoehe[wer]
    xn = np.clip(tcw, x0, x0 + du[wer])
    with np.errstate(divide="ignore", invalid="ignore"):
        zelt = hw * np.where(xn < tcw, xn / tcw, np.where(xn > tcw, (lw - xn) / (lw - tcw), 1.0))
    behalten = y0 <= zelt * (1 + 1e-9) + 1e-12
    wer, x0, y0 = wer[behalten], x0[behalten], y0[behalten]
    mitten = a[wer] + (x0 + du[wer] / 2)[:, None] * u[wer] + (y0 + dv[wer] / 2)[:, None] * v[wer]
    return mitten, wer, float(np.sqrt(du ** 2 + dv ** 2).max() / 2)


class Oberflaeche:
    """Dreiecksoberfläche mit exaktem Abstand Punkt → Oberfläche (ohne rtree/embree).

    Kandidaten über einen KD-Baum der Stützstellen (stuetzstellen), Abstand exakt zu jedem Kandidaten-Dreieck. Ein
    Abstand d gilt als belegt, wenn die k-te Stützstelle weiter als min(d, SICHER_MM) + Stützradius entfernt ist: dann
    ist kein ungeprüftes Dreieck näher. Abstände über SICHER_MM sind damit sicher ≥ SICHER_MM, ihr Wert kommt aus den
    geprüften Kandidaten (obere Schranke, praktisch exakt). Die Kriterien (≤ 0,3 mm) bleiben so streng belegt.
    """

    def __init__(self, dreiecke: np.ndarray):
        t = np.asarray(dreiecke, dtype=float).reshape(-1, 3, 3)
        ecken = t.reshape(-1, 3)
        diagonale = max(float(np.linalg.norm(ecken.max(axis=0) - ecken.min(axis=0))), 1e-9)
        flaeche = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
        self.dreiecke = t[flaeche > 1e-12 * diagonale ** 2]            # entartete Dreiecke tragen nichts bei
        schritt = diagonale / RASTER
        for _ in range(20):
            nu, nv = _raster(self.dreiecke, schritt)[-2:]
            zahl = int((nu * nv).sum())
            if zahl <= MAX_STUETZSTELLEN:
                break
            schritt *= 1.1 * np.sqrt(zahl / MAX_STUETZSTELLEN)
        mitten, self.zu_dreieck, self.radius = stuetzstellen(self.dreiecke, schritt)
        self.baum = cKDTree(mitten)

    def _naechste(self, p: np.ndarray, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Kleinster Abstand und Fußpunkt je Punkt p[i] über die Dreiecke der Stützstellen idx[i, :]."""
        m, k = idx.shape
        t = self.dreiecke[self.zu_dreieck[idx.ravel()]]
        q = naechster_punkt_dreieck(np.repeat(p, k, axis=0), t[:, 0], t[:, 1], t[:, 2]).reshape(m, k, 3)
        d = np.linalg.norm(q - p[:, None], axis=2)
        j = d.argmin(axis=1)
        r = np.arange(m)
        return d[r, j], q[r, j]

    def _block(self, p: np.ndarray, exakt: bool) -> tuple[np.ndarray, np.ndarray]:
        n = len(self.zu_dreieck)
        k = min(K_STUFEN[0], n)
        dk, idx = self.baum.query(p, k, eps=0 if exakt else GROB_EPS, workers=-1)
        dk, idx = dk.reshape(len(p), -1), idx.reshape(len(p), -1)
        d, q = self._naechste(p, idx)
        if not exakt:
            return d, q
        grenze = dk[:, -1] if k < n else np.full(len(p), np.inf)
        for k in K_STUFEN[1:]:
            offen = np.flatnonzero(grenze - self.radius < np.minimum(d, SICHER_MM))
            if not offen.size:
                return d, q
            k = min(k, n)
            dk, idx = self.baum.query(p[offen], k, workers=-1)
            d[offen], q[offen] = self._naechste(p[offen], idx.reshape(len(offen), -1))
            grenze[offen] = dk.reshape(len(offen), -1)[:, -1] if k < n else np.inf
        ziel = np.minimum(d, SICHER_MM)
        offen = np.flatnonzero(grenze - self.radius < ziel)
        for s in range(0, len(offen), 256):                     # Rückfall: alle Dreiecke in der Kugel ziel + Radius
            o = offen[s:s + 256]
            listen = self.baum.query_ball_point(p[o], ziel[o] + self.radius, workers=-1)
            wer = np.repeat(np.arange(len(o)), [len(x) for x in listen])
            idx = np.concatenate([np.asarray(x, dtype=np.intp) for x in listen])
            t = self.dreiecke[self.zu_dreieck[idx]]
            qq = naechster_punkt_dreieck(p[o][wer], t[:, 0], t[:, 1], t[:, 2])
            dd = np.linalg.norm(qq - p[o][wer], axis=1)
            folge = np.lexsort((dd, wer))
            _, erste = np.unique(wer[folge], return_index=True)
            beste = folge[erste]
            besser = dd[beste] < d[o]
            d[o[besser]], q[o[besser]] = dd[beste][besser], qq[beste][besser]
        return d, q

    def abstand(self, punkte: np.ndarray, exakt: bool = True) -> tuple[np.ndarray, np.ndarray]:
        """(Abstände, Fußpunkte) der Punkte zur Oberfläche. exakt=False: nur die ersten Kandidaten (obere Schranke)."""
        p = np.asarray(punkte, dtype=float).reshape(-1, 3)
        bloecke = [p[s:s + BLOCK] for s in range(0, len(p), BLOCK)]
        with ThreadPoolExecutor(max_workers=max(1, min(len(bloecke), FAEDEN, os.cpu_count() or 1))) as pool:
            teile = list(pool.map(lambda b: self._block(b, exakt), bloecke))   # numpy gibt dabei den GIL frei
        if not teile:
            return np.empty(0), np.empty((0, 3))
        return np.concatenate([t[0] for t in teile]), np.concatenate([t[1] for t in teile])


def lade(pfad: Path) -> trimesh.Trimesh:
    """STL (oder anderes Netzformat) als ein Netz; Szenen werden zusammengeführt."""
    netz = trimesh.load(Path(pfad), force="mesh")
    if not isinstance(netz, trimesh.Trimesh) or not len(netz.faces):
        raise ValueError(f"{pfad}: kein Dreiecksnetz")
    return netz


def stichprobe(netz: trimesh.Trimesh, anzahl: int, rng: np.random.Generator) -> np.ndarray:
    """Gleichmäßig über die Fläche verteilte Oberflächenpunkte."""
    flaechen = netz.area_faces
    welche = rng.choice(len(flaechen), size=anzahl, p=flaechen / flaechen.sum())
    r1, r2 = np.sqrt(rng.random(anzahl)), rng.random(anzahl)
    t = netz.triangles[welche]
    return (1 - r1)[:, None] * t[:, 0] + (r1 * (1 - r2))[:, None] * t[:, 1] + (r1 * r2)[:, None] * t[:, 2]


def flaechenschwerpunkt(netz: trimesh.Trimesh) -> np.ndarray:
    return (netz.triangles_center * netz.area_faces[:, None]).sum(axis=0) / netz.area


class _Seite:
    """Ein Netz, zentriert auf seinen Schwerpunkt, mit Stichprobe und Oberfläche."""

    def __init__(self, netz: trimesh.Trimesh, volumen_schwerpunkt: bool, punkte: int, rng: np.random.Generator):
        self.schwerpunkt = netz.center_mass if volumen_schwerpunkt else flaechenschwerpunkt(netz)
        self.punkte = stichprobe(netz, punkte, rng) - self.schwerpunkt
        self.oberflaeche = Oberflaeche(netz.triangles - self.schwerpunkt)
        self.huelle = netz.extents
        self.volumen = float(netz.volume)


def _abstaende(erg: _Seite, ref: _Seite, matrix: np.ndarray, anzahl: int | None, exakt: bool) -> np.ndarray:
    """Beidseitige Abstände: gedrehte Ergebnispunkte → Referenz, Referenzpunkte (rückgedreht) → Ergebnis."""
    pe = erg.punkte[:anzahl] @ matrix.T
    pr = ref.punkte[:anzahl] @ matrix          # Zeilenvektoren: x @ M = Mᵀ·x
    return np.concatenate([ref.oberflaeche.abstand(pe, exakt)[0], erg.oberflaeche.abstand(pr, exakt)[0]])


def _kennzahlen(erg: _Seite, ref: _Seite, matrix: np.ndarray, d: np.ndarray) -> dict:
    huelle_e = np.abs(matrix) @ erg.huelle
    vol_abw = abs(erg.volumen - ref.volumen) / abs(ref.volumen) * 100 if ref.volumen else float("inf")
    k = {
        "p99_mm": float(np.percentile(d, 99)),
        "max_mm": float(d.max()),
        "mittel_mm": float(d.mean()),
        "volumen_ergebnis": erg.volumen,
        "volumen_referenz": ref.volumen,
        "volumen_abw_prozent": float(vol_abw),
        "huelle_ergebnis": [float(x) for x in huelle_e],
        "huelle_referenz": [float(x) for x in ref.huelle],
        "huelle_abw_mm": float(np.abs(huelle_e - ref.huelle).max()),
        "matrix": [[float(x) for x in zeile] for zeile in matrix],
        "eigentlich": bool(np.linalg.det(matrix) > 0),
    }
    k["passt"] = passt(k)
    return k


def passt(k: dict) -> bool:
    """Kriterien der Spec §3: Volumen ±0,5 %, Hüllquader-Kanten ±0,3 mm, p99 ≤ 0,3 mm."""
    return bool(k["volumen_abw_prozent"] <= GRENZE_VOLUMEN_PROZENT and k["huelle_abw_mm"] <= GRENZE_HUELLE_MM
                and k["p99_mm"] <= GRENZE_P99_MM and k["max_mm"] <= GRENZE_MAX_MM)


def _rang(k: dict) -> tuple:
    return (not k["passt"], k["p99_mm"], k["mittel_mm"])


def vergleiche(ergebnis_stl: Path, referenz_stl: Path, *, punkte: int = 30000, saat: int = 0) -> dict:
    """Ergebnis gegen Referenz über alle 48 Achsenmatrizen; richtig = beste eigentliche passt."""
    netz_e, netz_r = lade(ergebnis_stl), lade(referenz_stl)
    volumen_schwerpunkt = bool(netz_e.is_volume and netz_r.is_volume)   # sonst beide Flächenschwerpunkt
    erg = _Seite(netz_e, volumen_schwerpunkt, punkte, np.random.default_rng([saat, 0]))
    ref = _Seite(netz_r, volumen_schwerpunkt, punkte, np.random.default_rng([saat, 1]))

    grob = []
    for m in achsenmatrizen():
        d = _abstaende(erg, ref, m, min(GROB_PUNKTE, punkte), exakt=False)
        grob.append((float(np.percentile(d, 99)), float(d.mean()), m))
    fein = {True: [], False: []}
    for art in (True, False):
        kandidaten = sorted((g for g in grob if (np.linalg.det(g[2]) > 0) == art), key=lambda g: g[:2])
        for _, _, m in kandidaten[:FEIN_JE_ART]:
            fein[art].append(_kennzahlen(erg, ref, m, _abstaende(erg, ref, m, None, exakt=True)))
    beste_e = min(fein[True], key=_rang)
    beste_u = min(fein[False], key=_rang)
    richtig = beste_e["passt"]
    gespiegelt = not richtig and beste_u["passt"]
    if richtig:
        beste = beste_e
    elif gespiegelt:
        beste = beste_u
    else:
        beste = min((beste_e, beste_u), key=_rang)
    return {
        "richtig": bool(richtig),
        "gespiegelt": bool(gespiegelt),
        "schwerpunkt": "volumen" if volumen_schwerpunkt else "flaeche",
        "beste": beste,
        "beste_eigentlich": beste_e,
        "beste_uneigentlich": beste_u,
    }


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("ergebnis", type=Path)
    a.add_argument("referenz", type=Path)
    a.add_argument("--punkte", type=int, default=30000)
    a.add_argument("--saat", type=int, default=0)
    args = a.parse_args()
    print(json.dumps(vergleiche(args.ergebnis, args.referenz, punkte=args.punkte, saat=args.saat),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
