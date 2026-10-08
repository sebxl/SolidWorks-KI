"""Geometrie-Steckbrief einer STL: Hüllquader, Volumen, Körper und achsparallele Zylinder – als dict und als Text.

Damit kann ein Agent ohne Bilder prüfen, ob Merkmale auf der richtigen Seite liegen (Spiegel-/Vorzeichenfehler).
Alle Längen in mm, Modellkoordinaten der STL. Braucht numpy, scipy und trimesh (Extra „messstand“).
"""

import math
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ACHSEN = "XYZ"
SEITEN = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
MAX_ZEILEN = 40

_SENKRECHT = 1e-3  # |n·a| darunter: Normale steht senkrecht zur Achse a
_PARALLEL = 1.0 - 1e-5  # |n·b| darüber: Normale parallel zur Hauptachse b (ebene Fläche, kein Mantel)
_MIN_DREIECKE = 6
_RMS_ANTEIL = 0.02  # zulässiger Kreis-Restfehler relativ zum Radius
_RADIAL = 0.9  # |cos| zwischen Normale und Radialrichtung je Dreieck
_BERUEHRT = 0.01
_BINS = 1440  # Winkelraster 0,25°


def steckbrief(stl: Path) -> dict:
    """Steckbrief einer STL (mm) als JSON-fähiges dict."""
    m = trimesh.load(Path(stl), file_type="stl", force="mesh", process=True)
    lo, hi = m.bounds
    zylinder = _zylinder(m)
    seiten = {}
    for k, a in enumerate(ACHSEN):
        for vz, wert in (("+", hi[k]), ("-", lo[k])):
            seite = vz + a
            treffer = []
            for i, z in enumerate(zylinder):
                if z["art"] == "aussen" and z["achse"] == a:
                    ende = z["bis"] if vz == "+" else z["von"]
                    if abs(ende - wert) < _BERUEHRT:
                        treffer.append(i)
                        z["beruehrt"].append(seite)
            seiten[seite] = {"koordinate": _r(wert), "zylinder": treffer}
    return {
        "huellquader": {"min": _rl(lo), "max": _rl(hi), "kanten": _rl(hi - lo)},
        "volumen_mm3": _r(m.volume),
        "flaeche_mm2": _r(m.area),
        "schwerpunkt": _rl(m.center_mass) if len(m.faces) else [0.0, 0.0, 0.0],
        "koerper": _komponenten(len(m.faces), m.face_adjacency)[0],
        "zylinder": zylinder,
        "seiten": {s: seiten[s] for s in SEITEN},
    }


def als_text(sb: dict) -> str:
    """Kompakte deutsche Textform (höchstens MAX_ZEILEN Zeilen, 0,01 mm, Dezimalkomma)."""
    h = sb["huellquader"]
    bereiche = "  ".join(f"{a} {_z(h['min'][k])}…{_z(h['max'][k])}" for k, a in enumerate(ACHSEN))
    zeilen = [
        f"Hüllquader {bereiche}  ({' × '.join(_z(v) for v in h['kanten'])})",
        f"Volumen {_z(sb['volumen_mm3'])} mm³  Oberfläche {_z(sb['flaeche_mm2'])} mm²  "
        f"Schwerpunkt ({' | '.join(_z(v) for v in sb['schwerpunkt'])})  Körper {sb['koerper']}",
    ]
    platz = MAX_ZEILEN - len(zeilen)
    einzeln = [_zylinder_zeile(z, [z["mitte"]]) for z in sb["zylinder"]]
    if len(einzeln) <= platz:
        return "\n".join(zeilen + einzeln)
    gruppen: dict[tuple, list] = {}
    for z in sb["zylinder"]:
        schluessel = (z["art"], z["achse"], _z(z["durchmesser"]), _z(z["von"]), _z(z["bis"]),
                      round(z["winkel_grad"]), tuple(z["beruehrt"]))
        gruppen.setdefault(schluessel, [z, []])[1].append(z["mitte"])
    gruppiert = [_zylinder_zeile(z, mitten) for z, mitten in gruppen.values()]
    if len(gruppiert) > platz:
        rest = len(gruppiert) - (platz - 1)
        gruppiert = gruppiert[: platz - 1] + [f"… {rest} weitere Zylinderzeilen (siehe Steckbrief-dict)"]
    return "\n".join(zeilen + gruppiert)


# --- Zylinder ---------------------------------------------------------------------------------------------------


def _zylinder(m) -> list[dict]:
    """Achsparallele zylindrische Flächenstücke, Bögen gleicher Achse/Mitte/Radius zusammengefasst."""
    if not len(m.faces):
        return []
    normalen = m.face_normals
    gueltig = (np.linalg.norm(normalen, axis=1) > 0.5) & (m.area_faces > 1e-12)
    adj = m.face_adjacency
    boegen = []
    for k in range(3):
        q = [i for i in range(3) if i != k]
        kand = (gueltig & (np.abs(normalen[:, k]) < _SENKRECHT)
                & (np.abs(normalen[:, q[0]]) < _PARALLEL) & (np.abs(normalen[:, q[1]]) < _PARALLEL))
        idx = np.nonzero(kand)[0]
        if len(idx) < _MIN_DREIECKE:
            continue
        lokal = np.full(len(m.faces), -1)
        lokal[idx] = np.arange(len(idx))
        paare = lokal[adj[kand[adj[:, 0]] & kand[adj[:, 1]]]]
        _, label = _komponenten(len(idx), paare)
        groesse = np.bincount(label)
        ordnung = np.argsort(label, kind="stable")
        grenzen = np.cumsum(groesse)[:-1]
        for g, gruppe in enumerate(np.split(idx[ordnung], grenzen)):
            if groesse[g] >= _MIN_DREIECKE:
                bogen = _bogen(m, gruppe, k)
                if bogen:
                    boegen.append(bogen)
    zylinder = [_als_dict(b) for b in _vereinen(m, boegen)]
    zylinder.sort(key=lambda z: (-z["durchmesser"], z["achse"], z["art"], *z["mitte"].values(), z["von"]))
    return zylinder


def _bogen(m, flaechen, k) -> dict | None:
    """Kreis-Fit eines Flächenstücks quer zur Achse k; None, wenn es kein Zylindermantel ist."""
    q = [i for i in range(3) if i != k]
    ecken = m.faces[flaechen]
    punkte_idx = np.unique(ecken)
    p = m.vertices[punkte_idx][:, q]
    schwer = p.mean(axis=0)
    d = p - schwer
    a = np.c_[d, np.ones(len(d))]
    loes, *_ = np.linalg.lstsq(a, -(d**2).sum(axis=1), rcond=None)
    c = -loes[:2] / 2
    r2 = c @ c - loes[2]
    if not np.isfinite(r2) or r2 <= 0:
        return None
    r = math.sqrt(r2)
    diagonale = float(np.linalg.norm(m.extents))
    if r > diagonale:
        return None
    rms = math.sqrt(np.mean((np.linalg.norm(d - c, axis=1) - r) ** 2))
    if rms > _RMS_ANTEIL * r:
        return None
    # Normalen müssen radial zeigen – alle nach außen (Zapfen) oder alle nach innen (Bohrung).
    radial = m.triangles_center[flaechen][:, q] - schwer - c
    radial /= np.linalg.norm(radial, axis=1)[:, None]
    n2 = m.face_normals[flaechen][:, q]
    n2 = n2 / np.linalg.norm(n2, axis=1)[:, None]
    cos = (radial * n2).sum(axis=1)
    if np.all(cos > _RADIAL):
        art = "aussen"
    elif np.all(cos < -_RADIAL):
        art = "innen"
    else:
        return None
    winkel = _winkel(m.vertices[ecken][:, :, q] - schwer - c)
    if winkel < 1.0:
        return None
    entlang = m.vertices[punkte_idx][:, k]
    return {"k": k, "c": c + schwer, "r": r, "art": art, "flaechen": flaechen, "winkel": winkel,
            "von": float(entlang.min()), "bis": float(entlang.max())}


def _winkel(ecken2d) -> float:
    """Überdeckter Bogenwinkel in Grad; Lücken bis 1,5 Facettenbreiten (achsparallele Facetten) gelten als gedeckt."""
    w = np.arctan2(ecken2d[:, :, 1], ecken2d[:, :, 0])
    rel = (w - w[:, :1] + np.pi) % (2 * np.pi) - np.pi
    start = w[:, 0] + rel.min(axis=1)
    breite = rel.max(axis=1) - rel.min(axis=1)
    schritt = 2 * np.pi / _BINS
    s = np.floor((start % (2 * np.pi)) / schritt).astype(int)
    e = s + np.ceil(breite / schritt).astype(int) + 1
    diff = np.zeros(2 * _BINS + 2, dtype=int)
    np.add.at(diff, s, 1)
    np.add.at(diff, np.minimum(e, 2 * _BINS + 1), -1)
    lauf = np.cumsum(diff)[: 2 * _BINS]
    gedeckt = (lauf[:_BINS] + lauf[_BINS:]) > 0
    if gedeckt.all():
        return 360.0
    if not gedeckt.any():
        return 0.0
    # Lücken (zyklisch) füllen, die nicht breiter als 1,5 Facetten sind.
    max_luecke = int(math.ceil(1.5 * breite.max() / schritt)) + 2
    versatz = int(np.argmax(gedeckt))  # beginnt mit gedecktem Bin
    rund = np.roll(gedeckt, -versatz)
    i = 0
    while i < _BINS:
        if rund[i]:
            i += 1
            continue
        j = i
        while j < _BINS and not rund[j]:
            j += 1
        if j - i <= max_luecke:
            rund[i:j] = True
        i = j
    return 360.0 if rund.all() else float(rund.sum()) * 360.0 / _BINS


def _vereinen(m, boegen) -> list[dict]:
    """Bögen gleicher Achse, Art, Mitte und Radius mit überlappender Achslänge zusammenfassen und neu fitten."""
    eltern = list(range(len(boegen)))

    def wurzel(i):
        while eltern[i] != i:
            eltern[i] = eltern[eltern[i]]
            i = eltern[i]
        return i

    for i, a in enumerate(boegen):
        for j in range(i + 1, len(boegen)):
            b = boegen[j]
            tol = max(0.02, 0.01 * a["r"])
            if (a["k"] == b["k"] and a["art"] == b["art"] and abs(a["r"] - b["r"]) < tol
                    and np.linalg.norm(a["c"] - b["c"]) < tol
                    and a["von"] <= b["bis"] + _BERUEHRT and b["von"] <= a["bis"] + _BERUEHRT):
                eltern[wurzel(j)] = wurzel(i)
    sammlung: dict[int, list] = {}
    for i in range(len(boegen)):
        sammlung.setdefault(wurzel(i), []).append(boegen[i])
    ergebnis = []
    for teile in sammlung.values():
        if len(teile) == 1:
            ergebnis.append(teile[0])
            continue
        neu = _bogen(m, np.concatenate([t["flaechen"] for t in teile]), teile[0]["k"])
        ergebnis.extend([neu] if neu else teile)
    return ergebnis


def _als_dict(b) -> dict:
    q = [ACHSEN[i] for i in range(3) if i != b["k"]]
    return {
        "achse": ACHSEN[b["k"]],
        "mitte": {q[0].lower(): _r(b["c"][0]), q[1].lower(): _r(b["c"][1])},
        "durchmesser": _r(2 * b["r"]),
        "von": _r(b["von"]),
        "bis": _r(b["bis"]),
        "art": b["art"],
        "winkel_grad": round(b["winkel"], 1),
        "beruehrt": [],
    }


# --- Hilfen -----------------------------------------------------------------------------------------------------


def _komponenten(n: int, paare) -> tuple[int, np.ndarray]:
    """Zusammenhangskomponenten von n Knoten mit Kantenliste paare (k×2)."""
    if n == 0:
        return 0, np.zeros(0, dtype=int)
    paare = np.asarray(paare).reshape(-1, 2)
    g = coo_matrix((np.ones(len(paare)), (paare[:, 0], paare[:, 1])), shape=(n, n))
    anzahl, label = connected_components(g, directed=False)
    return int(anzahl), label


def _zylinder_zeile(z: dict, mitten: list[dict]) -> str:
    achse = z["achse"]
    kopf = "Zylinder außen" if z["art"] == "aussen" else "Bohrung"
    anzahl = f" {len(mitten)}×" if len(mitten) > 1 else ""
    teile = [f"{kopf}{anzahl} Ø{_z(z['durchmesser'])}", f"Achse {achse}"]
    lage = ["  ".join(f"{a} {_z(v)}" for a, v in m.items()) for m in mitten]
    teile.append("Mitte " + lage[0] if len(lage) == 1 else "Mitten " + "; ".join(lage))
    teile.append(f"{achse.lower()} {_z(z['von'])}…{_z(z['bis'])}")
    if z["winkel_grad"] < 359.5:
        teile.append(f"Bogen {round(z['winkel_grad'])}°")
    if z["beruehrt"]:
        teile.append("(berührt " + ", ".join(s.replace("-", "−") for s in z["beruehrt"]) + ")")
    return "  ".join(teile)


def _r(v) -> float:
    return round(float(v), 4) + 0.0


def _rl(v) -> list[float]:
    return [_r(x) for x in v]


def _z(v: float) -> str:
    """Zahl für den Text: 0,01 mm, ohne überflüssige Nullen, Dezimalkomma, echtes Minuszeichen."""
    w = round(float(v), 2) + 0.0
    s = f"{w:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",").replace("-", "−")
