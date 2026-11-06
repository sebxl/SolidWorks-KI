"""typ austragung (Paket Konstruktionsstil, Spike S20 e): Profil entlang eines offenen Pfads – Geometrie des Pfads in
mm und die Befunde von validieren, ohne SolidWorks.

Profil und Pfad liegen auf Standard- oder Versatzebenen. Das Profil steht senkrecht auf dem ersten Segment und seine
Mitte liegt auf dem Pfadanfang; der Pfad ist tangentenstetig, jeder Bogen weiter als das halbe Profil.
"""

import math

from swki.spec.ausdruck import AusdruckFehler, auswerten

_NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_TOL = 1e-6


def _ebene(ebene) -> tuple[str, float, dict | str]:
    """(Orientierung, Lage der Ebene in mm roh, Ebene) einer Standard- oder Versatzebene."""
    if isinstance(ebene, str):
        return ebene, 0, ebene
    return ebene["versatz"]["ebene"], ebene["versatz"]["abstand"], ebene


def modell(orientierung: str, u: float, v: float, lage: float) -> tuple[float, float, float]:
    """(u, v) einer Skizze auf einer Standard- bzw. Versatzebene → Modellkoordinaten (wie swki.compiler.skizze)."""
    if orientierung == "vorne":
        return (u, v, lage)
    if orientierung == "oben":
        return (u, lage, -v)
    return (lage, v, -u)


def _punkt(q, p) -> tuple[float, float]:
    return (auswerten(q[0], p), auswerten(q[1], p))


def segmente_uv(pfad: dict, p: dict) -> list[dict]:
    """Je Segment Anfang a, Ende b, Richtung am Anfang und am Ende (Einheitsvektoren in uv), Länge; Bögen mit Radius."""
    aus = []
    a = _punkt(pfad["start"], p)
    for s in pfad["segmente"]:
        if "linie" in s:
            b = _punkt(s["linie"], p)
            d = (b[0] - a[0], b[1] - a[1])
            n = math.hypot(*d)
            t = (d[0] / n, d[1] / n) if n > _TOL else (0.0, 0.0)
            aus.append({"a": a, "b": b, "t_a": t, "t_b": t, "laenge": n, "radius": None})
        else:
            b, m = _punkt(s["bogen"], p), _punkt(s["mitte"], p)
            sinn = -1.0 if s.get("uhrzeigersinn") else 1.0
            r = math.hypot(a[0] - m[0], a[1] - m[1])
            r_ende = math.hypot(b[0] - m[0], b[1] - m[1])
            wa, wb = math.atan2(a[1] - m[1], a[0] - m[0]), math.atan2(b[1] - m[1], b[0] - m[0])
            winkel = (sinn * (wb - wa)) % (2 * math.pi)

            def tangente(w: float) -> tuple[float, float]:
                return (-sinn * math.sin(w), sinn * math.cos(w))

            aus.append({"a": a, "b": b, "t_a": tangente(wa), "t_b": tangente(wb), "laenge": r * winkel, "radius": r,
                        "radius_ende": r_ende})
        a = b
    return aus


def pfad_laenge(pfad: dict, p: dict) -> float:
    return sum(s["laenge"] for s in segmente_uv(pfad, p))


def profil_halbe_groesse(element: dict, p: dict) -> float:
    if "kreis" in element:
        return auswerten(element["kreis"]["durchmesser"], p) / 2
    r = element["rechteck"]
    return math.hypot(auswerten(r["breite"], p), auswerten(r["hoehe"], p)) / 2


def befunde(f: dict, pfad: str, p: dict) -> list[dict]:
    """validieren: Profil senkrecht am Pfadanfang, offener tangentenstetiger Pfad, Bögen weiter als das halbe Profil.
    Ausdrucksfehler meldet validieren an anderer Stelle."""
    try:
        segmente = segmente_uv(f["pfad"], p)
        [element] = f["profil"]["elemente"]
        art = "kreis" if "kreis" in element else "rechteck"
        mitte = _punkt(element[art]["mitte"], p)
        o_prof, lage_prof, _ = _ebene(f["profil"]["ebene"])
        o_pfad, lage_pfad, _ = _ebene(f["pfad"]["ebene"])
        lage_prof, lage_pfad = auswerten(lage_prof, p), auswerten(lage_pfad, p)
        halb = profil_halbe_groesse(element, p)
    except AusdruckFehler:
        return []
    aus = []

    def melde(stelle: str, meldung: str) -> None:
        aus.append({"pfad": f"{pfad}.{stelle}", "meldung": meldung})

    start = segmente[0]["a"]
    ende = segmente[-1]["b"]
    if math.dist(start, ende) <= _TOL:
        melde("pfad", "der Pfad ist geschlossen: austragung braucht einen offenen Pfad (Anfang ≠ Ende)")
    richtung = modell(o_pfad, *segmente[0]["t_a"], 0.0)
    normale = _NORMALE[o_prof]
    if abs(abs(sum(a * b for a, b in zip(richtung, normale))) - 1) > _TOL:
        melde("profil.ebene", "die Profilebene steht nicht senkrecht auf dem ersten Segment des Pfads")
    elif math.dist(modell(o_prof, *mitte, lage_prof), modell(o_pfad, *start, lage_pfad)) > _TOL:
        melde("profil", "die Mitte des Profils liegt nicht auf dem Anfang des Pfads")
    for k, s in enumerate(segmente):
        if s["laenge"] <= _TOL:
            melde(f"pfad.segmente[{k}]", "Segment ohne Länge")
        if s["radius"] is not None and (s["radius"] <= _TOL or abs(s["radius_ende"] - s["radius"]) > _TOL):
            melde(f"pfad.segmente[{k}]", f"Bogen: Anfang und Ende liegen nicht gleich weit von der Mitte "
                                         f"({s['radius']:g} / {s['radius_ende']:g})")
        elif s["radius"] is not None and s["radius"] <= halb + _TOL:
            melde(f"pfad.segmente[{k}]", f"Bogen R {s['radius']:g} ist nicht weiter als das halbe Profil ({halb:g}): "
                                         "die Austragung schneidet sich selbst")
        vorher = segmente[k - 1]["t_b"] if k else None
        if vorher and (abs(s["t_a"][0] * vorher[1] - s["t_a"][1] * vorher[0]) > _TOL
                       or s["t_a"][0] * vorher[0] + s["t_a"][1] * vorher[1] < 0):
            melde(f"pfad.segmente[{k}]", "Knick im Pfad: Segmente tangential aneinander anschließen (Bogen dazwischen)")
    return aus
