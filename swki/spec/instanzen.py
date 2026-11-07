"""Instanzen gemusterter und gespiegelter Bohrungen (Paket Konstruktionsstil, Spike S20).

Reihenfolge: erst die Positionen der Bohrung, dann je Muster/Spiegelung, das sie trägt, dessen Kopien in
Spec-Reihenfolge; innerhalb eines Musters versatzweise (Richtung 1 außen, Richtung 2 innen), je Versatz alle Punkte der
Quellen. `{feature: <bohrung>, instanz: n}` zählt so, ebenso `je_position` einer Baugruppe. Punkte in mm.
"""

import math

from swki.compiler.anker import ACHSEN, Vektor
from swki.spec.ausdruck import auswerten

MUSTER = ("muster_linear", "muster_kreis", "spiegeln")

# Richtung der Referenzachsen achse_x/y/z, um die ein Kreismuster dreht (rechtsdrehend um diese Richtung).
# x live belegt 07.11.2026 (tests/live/test_live_musterinstanzen.py::test_bezugsachsen_wie_konstante); y, z Spike S20 d
# (achse_y zeigt nach −y).
BEZUGSACHSE: dict[str, tuple[float, float, float]] = {"x": (1.0, 0.0, 0.0), "y": (0.0, -1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def faktor(f: dict) -> int:
    """Instanzen je Quellinstanz (die Quelle mitgezählt)."""
    if f["typ"] == "muster_linear":
        return f["richtung1"]["anzahl"] * f.get("richtung2", {}).get("anzahl", 1)
    if f["typ"] == "muster_kreis":
        return f["anzahl"]
    return 2


def traeger(spec: dict, fid: str) -> list[str]:
    """IDs der Muster und Spiegelungen, die Instanzen von `fid` tragen (direkt oder über ein früheres Muster)."""
    ergebnis: list[str] = []
    for f in spec.get("features", []):
        if f.get("typ") in MUSTER and (fid in f["features"] or any(t in f["features"] for t in ergebnis)):
            ergebnis.append(f["id"])
    return ergebnis


def anzahl_instanzen(spec: dict, fid: str) -> int:
    """Positionen der Bohrung plus alle Kopien ihrer Träger."""
    nach_id = {f["id"]: f for f in spec.get("features", [])}
    eigene = len(nach_id[fid].get("positionen", [None]))
    beitrag: dict[str, int] = {}
    for t in traeger(spec, fid):
        m = nach_id[t]
        in_quellen = (eigene if fid in m["features"] else 0) + sum(beitrag.get(q, 0) for q in m["features"])
        beitrag[t] = (faktor(m) - 1) * in_quellen
    return eigene + sum(beitrag.values())


def _schritt(richtung: dict, parameter: dict) -> Vektor:
    e = ACHSEN[richtung["achse"]]
    a = auswerten(richtung["abstand"], parameter) * (-1 if richtung.get("umkehren") else 1)
    return (e[0] * a, e[1] * a, e[2] * a)


def kopien_linear(punkte: list[Vektor], richtung1: dict, richtung2: dict | None, parameter: dict) -> list[Vektor]:
    """Kopien eines linearen Musters (ohne die Quelle); die Richtung folgt der Achse, `umkehren` dreht sie (wie der
    Handler sie in SolidWorks setzt)."""
    s1 = _schritt(richtung1, parameter)
    s2 = _schritt(richtung2, parameter) if richtung2 else (0.0, 0.0, 0.0)
    n2 = richtung2["anzahl"] if richtung2 else 1
    return [tuple(p[i] + k1 * s1[i] + k2 * s2[i] for i in range(3))
            for k1 in range(richtung1["anzahl"]) for k2 in range(n2) if (k1, k2) != (0, 0) for p in punkte]


def kopien_kreis(punkte: list[Vektor], achse: Vektor, anzahl: int, winkel: float) -> list[Vektor]:
    """Kopien eines Kreismusters um eine Achse durch den Ursprung: rechtsdrehend um die Achsrichtung, Schritt 360°/n
    beim Vollkreis, sonst Winkel/(n − 1) (Spike S20 d)."""
    schritt = math.radians(360 / anzahl if winkel == 360 else winkel / (anzahl - 1))
    k = achse
    aus = []
    for i in range(1, anzahl):
        w = i * schritt
        c, s = math.cos(w), math.sin(w)
        for p in punkte:
            kxp = (k[1] * p[2] - k[2] * p[1], k[2] * p[0] - k[0] * p[2], k[0] * p[1] - k[1] * p[0])
            kp = k[0] * p[0] + k[1] * p[1] + k[2] * p[2]
            aus.append(tuple(p[j] * c + kxp[j] * s + k[j] * kp * (1 - c) for j in range(3)))  # Rodrigues
    return aus


def kopien_spiegeln(punkte: list[Vektor], achse_index: int, lage: float) -> list[Vektor]:
    """Spiegelbilder an der Ebene `Koordinate[achse_index] = lage`."""
    return [tuple(2 * lage - c if i == achse_index else c for i, c in enumerate(p)) for p in punkte]
