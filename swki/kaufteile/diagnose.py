"""Übersicht der Flächen eines importierten Kaufteils für `swki kaufteil untersuchen` (Spec 3c §5.1), ohne SolidWorks.

Eingabe: je ebener oder zylindrischer Fläche ein Datensatz der SolidWorks-Schicht {"art", "punkt", "normale" | "achse",
"radius", "auf" (Punkt auf der begrenzten Fläche), "flaeche_mm2"}. Ausgabe: Zylinder gleicher Achse und gleichen Radius
bzw. Ebenen gleicher Lage und Normale zusammengefasst, die größten zuerst, je Art höchstens `grenze` Einträge. Die
Punkte "nahe" taugen als Ankerpunkte für den Katalogeintrag."""

from swki.compiler.anker import laenge, skalar


def _r(v, n: int = 4) -> list[float]:
    return [round(c, n) + 0.0 for c in v]


def _richtung(v) -> tuple:
    """Einheitsvektor mit festem Vorzeichen (erste Komponente ≠ 0 positiv): Achsen ohne Richtungssinn vergleichen."""
    n = laenge(v)
    e = tuple(c / n for c in v)
    erste = next(c for c in e if abs(c) > 1e-9)
    return tuple(-c for c in e) if erste < 0 else e


def _fusspunkt(punkt, richtung) -> tuple:
    """Punkt der Achse, der dem Ursprung am nächsten liegt (gleiche Achse → gleicher Fußpunkt)."""
    t = skalar(punkt, richtung)
    return tuple(punkt[i] - t * richtung[i] for i in range(3))


def uebersicht(saetze: list[dict], grenze: int = 50) -> dict:
    zylinder: dict[tuple, dict] = {}
    ebenen: dict[tuple, dict] = {}
    for s in saetze:
        if s["art"] == "zylinder":
            richtung = _richtung(s["achse"])
            schluessel = (round(s["radius"], 4), *_r(richtung, 6), *_r(_fusspunkt(s["punkt"], richtung), 3))
            z = zylinder.setdefault(schluessel, {"durchmesser": round(2 * s["radius"], 4),
                                                 "achspunkt": _r(_fusspunkt(s["punkt"], richtung)),
                                                 "richtung": _r(richtung, 6), "nahe": _r(s["auf"]), "flaechen": 0,
                                                 "flaeche_mm2": 0.0, "_groesste": 0.0})
        else:
            n = tuple(s["normale"])
            schluessel = (*_r(n, 6), round(skalar(s["punkt"], n), 3))
            z = ebenen.setdefault(schluessel, {"normale": _r(n, 6), "abstand": round(skalar(s["punkt"], n), 4),
                                               "nahe": _r(s["auf"]), "flaechen": 0, "flaeche_mm2": 0.0, "_groesste": 0.0})
        z["flaechen"] += 1
        z["flaeche_mm2"] += s["flaeche_mm2"]
        if s["flaeche_mm2"] > z["_groesste"]:
            z["_groesste"], z["nahe"] = s["flaeche_mm2"], _r(s["auf"])

    def liste(gruppen: dict) -> list[dict]:
        sortiert = sorted(gruppen.values(), key=lambda g: g["flaeche_mm2"], reverse=True)[:grenze]
        return [{**{k: v for k, v in g.items() if k != "_groesste"}, "flaeche_mm2": round(g["flaeche_mm2"], 2)}
                for g in sortiert]

    return {"zylinder": liste(zylinder), "ebenen": liste(ebenen), "zylinder_gesamt": len(zylinder),
            "ebenen_gesamt": len(ebenen)}
