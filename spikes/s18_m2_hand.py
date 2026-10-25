"""S18 M2b: Simulationsgeometrie aus den Specs gegen das Handmodell der Sortierschritt-Studie (modell.geometrie(var)).

Je Gruppe (Kanal, Glas, Durchlicht, Schieber, Keil, Rutsche, Träger) Monte-Carlo-Stichprobe im gemeinsamen Hüllquader:
Volumen nur im Handmodell / nur in der Spec, dazu die Orte der Unterschiede (zusammenhängende 1-mm-Zellen, größte
zuerst) – so wird sichtbar, was das Handmodell vereinfacht oder anders hat. Beide Modelle in Grundstellung
(Schieber Pos. 1, Keil eingefahren), Maschinenkoordinaten mm.

Aufruf: .venv-sim\\Scripts\\python.exe -m spikes.s18_m2_hand <geometrie.json> <ausgabe.json> [--var G1c] [--punkte 3000000]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

from spikes.s18_sim import M

GRUPPE_SPEC = {"boden": "kanal", "wand_l": "kanal", "wand_r": "kanal", "glas": "glas", "durchlicht": "durchlicht",
               "schieber": "schieber", "zwischenplatte": "keil", "keil": "keil", "rutsche_": "rutsche",
               "rutschentraeger": "traeger"}
GRUPPE_HAND = {"kanal": "kanal", "glas": "glas", "durchlicht": "durchlicht", "schieber": "schieber", "keil": "keil",
               "rutsche": "rutsche", "traeger": "traeger"}


def _punkte(e) -> np.ndarray:
    if e["art"] == "box":
        (a, b) = e["daten"]
        return np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])], float)
    return np.array(e["daten"], float).reshape(-1, 3)


def _huellen(eintraege) -> list:
    out = []
    for e in eintraege:
        p = _punkte(e)
        h = ConvexHull(p)
        out.append((p.min(0), p.max(0), h.equations))
    return out


def _innen(pts: np.ndarray, huellen) -> np.ndarray:
    drin = np.zeros(len(pts), bool)
    for lo, hi, eq in huellen:
        m = np.all((pts >= lo - 1e-9) & (pts <= hi + 1e-9), axis=1) & ~drin
        if not m.any():
            continue
        q = pts[m]
        drin[np.flatnonzero(m)[np.all(q @ eq[:, :3].T + eq[:, 3] <= 1e-7, axis=1)]] = True
    return drin


def orte(pts: np.ndarray, lo: np.ndarray, zelle: float, dv: float, top: int = 6) -> list:
    if not len(pts):
        return []
    idx = np.floor((pts - lo) / zelle).astype(int)
    form = idx.max(0) + 1
    gitter = np.zeros(form, np.int32)
    np.add.at(gitter, tuple(idx.T), 1)
    marke, n = ndimage.label(gitter > 0, structure=np.ones((3, 3, 3)))
    out = []
    for k in range(1, n + 1):
        sel = marke[tuple(idx.T)] == k
        q = pts[sel]
        out.append(dict(volumen_mm3=round(sel.sum() * dv, 1), von=[round(float(c), 1) for c in q.min(0)],
                        bis=[round(float(c), 1) for c in q.max(0)]))
    return sorted(out, key=lambda o: -o["volumen_mm3"])[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geometrie"); ap.add_argument("ausgabe")
    ap.add_argument("--var", default="G1c"); ap.add_argument("--punkte", type=int, default=3_000_000)
    a = ap.parse_args()
    spec = json.loads(Path(a.geometrie).read_text(encoding="utf-8"))["geometrie"]
    hand = [e for e in M.geometrie(a.var) if e["stoss"]]
    gs, gh = defaultdict(list), defaultdict(list)
    for e in spec:
        praefix = next(p for p in sorted(GRUPPE_SPEC, key=len, reverse=True) if e["name"].startswith(p))
        gs[GRUPPE_SPEC[praefix]].append(e)
    for e in hand:
        gh[GRUPPE_HAND.get(e["gruppe"], e["gruppe"])].append(e)
    rng = np.random.default_rng(1)
    erg = {}
    for g in sorted(set(gs) | set(gh)):
        hs, hh = _huellen(gs.get(g, [])), _huellen(gh.get(g, []))
        alle = np.vstack([np.vstack([lo, hi]) for lo, hi, _ in hs + hh])
        lo, hi = alle.min(0) - 0.5, alle.max(0) + 0.5
        vol = float(np.prod(hi - lo))
        pts = lo + rng.random((a.punkte, 3)) * (hi - lo)
        s, h = _innen(pts, hs), _innen(pts, hh)
        dv = vol / a.punkte
        nur_h, nur_s = pts[h & ~s], pts[s & ~h]
        erg[g] = dict(volumen_spec=round(s.sum() * dv, 1), volumen_hand=round(h.sum() * dv, 1),
                      nur_hand=round(len(nur_h) * dv, 1), nur_spec=round(len(nur_s) * dv, 1),
                      aufloesung_mm3=round(dv, 4), orte_nur_hand=orte(nur_h, lo, 1.0, dv),
                      orte_nur_spec=orte(nur_s, lo, 1.0, dv))
        print(g, {k: v for k, v in erg[g].items() if not k.startswith("orte")})
        for k in ("orte_nur_hand", "orte_nur_spec"):
            for o in erg[g][k][:4]:
                print("   ", k, o)
    Path(a.ausgabe).write_text(json.dumps(erg, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
