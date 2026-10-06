"""Einbaureferenzen und Gewindepositionen in fremder Geometrie orten und gegenprüfen (Spec 3c §4.2, §4.3).

Reine Geometrie auf den Flächen aller Körper (swki.compiler.anker.Flaeche, mm). Für zylinder und ebene setzt die
SolidWorks-Schicht vorher .abstand jeder Fläche zum Punkt `nahe` (swki.compiler.topologie.mit_abstand, echter Abstand
zur begrenzten Fläche); Gewindepositionen brauchen nur die Achslage."""

import math
from dataclasses import dataclass, field

from swki.compiler.anker import AnkerFehler, Flaeche, Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.spec.normen import normmasse

TOL_DURCHMESSER = 0.01   # mm, Gegenprobe Ø (Spec 3c §4.2)
TOL_WINKEL_GRAD = 0.01   # Gegenprobe Normale, Lage der Referenzen zueinander
ABSTAND_ACHSE_MIN = 1.0  # mm: ebene_durch_achse braucht einen Punkt neben der Achse
_GLEICH_MM = 1e-4


@dataclass
class Ortung:
    name: str                 # EINBAU_* bzw. "<gruppe>.<i>"
    art: str                  # zylinder | ebene | ebene_durch_achse | gewinde
    flaeche: Flaeche | None   # geortete Fläche (ebene_durch_achse: None)
    ist: dict = field(default_factory=dict)  # gemessene Werte (durchmesser, normale, punkt, modell …)
    abweichung: str | None = None            # Gegenprobe verfehlt; None = bestanden


def einheit(v: Vektor) -> Vektor:
    n = laenge(v)
    return tuple(c / n for c in v)


def kreuz(a: Vektor, b: Vektor) -> Vektor:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def winkel_grad(a: Vektor, b: Vektor) -> float:
    """Winkel zwischen zwei Richtungen (0 … 180°)."""
    c = skalar(einheit(a), einheit(b))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def kandidaten(flaechen: list[Flaeche], art: str, punkt: Vektor, tol_mm: float) -> list[Flaeche]:
    """Flächen der Art (ebene | zylinder), deren unendliche Fläche höchstens tol_mm vom Punkt liegt: Vorauswahl, bevor
    die SolidWorks-Schicht den echten Abstand misst (ein COM-Aufruf je Fläche)."""
    if art == "ebene":
        return [f for f in flaechen if f.art == "ebene" and abs(skalar(differenz(punkt, f.punkt), f.normale)) <= tol_mm]
    return [f for f in flaechen if f.art == "zylinder"
            and abs(punkt_achse_abstand(punkt, f.punkt, einheit(f.achse)) - f.radius) <= tol_mm]


def _innerhalb(kandidaten: list[Flaeche], tol_mm: float, was: str, punkt) -> list[Flaeche]:
    if not kandidaten:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} innerhalb {tol_mm:g} mm um {list(punkt)}")
    innen = [f for f in kandidaten if f.abstand <= tol_mm]
    if not innen:
        naechste = min(f.abstand for f in kandidaten)
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} innerhalb {tol_mm:g} mm um {list(punkt)} "
                                                   f"(nächste {naechste:.3f} mm)")
    return innen


def orte_zylinder(flaechen: list[Flaeche], name: str, w: dict, tol_mm: float) -> Ortung:
    """Zylinderfläche durch `nahe`; Flächen gleicher Achse und gleichen Radius (geteilter Mantel, Welle in Bohrung)
    gelten als eine. Gegenprobe Ø."""
    innen = _innerhalb([f for f in flaechen if f.art == "zylinder"], tol_mm, "Zylinderfläche", w["nahe"])
    erste = innen[0]
    for f in innen[1:]:
        gleich = (abs(f.radius - erste.radius) <= _GLEICH_MM and abs(abs(skalar(einheit(f.achse), einheit(erste.achse))) - 1) < 1e-9
                  and punkt_achse_abstand(f.punkt, erste.punkt, einheit(erste.achse)) <= _GLEICH_MM)
        if not gleich:
            raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{name}: {len(innen)} verschiedene Zylinderflächen innerhalb "
                                                   f"{tol_mm:g} mm um {list(w['nahe'])}")
    d = 2 * erste.radius
    abweichung = None if abs(d - w["durchmesser"]) <= TOL_DURCHMESSER else f"Ø {d:.4f} statt {w['durchmesser']:g}"
    return Ortung(name, "zylinder", erste, {"durchmesser": round(d, 6), "achse": einheit(erste.achse),
                                            "punkt": erste.punkt}, abweichung)


def orte_ebene(flaechen: list[Flaeche], name: str, w: dict, tol_mm: float) -> Ortung:
    """Ebene Fläche durch `nahe`. Unter mehreren nahen Flächen zählen die mit passender Normale (zwei Körper können
    sich in einer Ebene berühren); passt keine, ist die nächste mit abweichender Normale das Ergebnis der Gegenprobe."""
    innen = _innerhalb([f for f in flaechen if f.art == "ebene"], tol_mm, "ebene Fläche", w["nahe"])
    soll = einheit(tuple(w["normale"]))
    passend = [f for f in innen if winkel_grad(f.normale, soll) <= TOL_WINKEL_GRAD]
    ebenen = {round(skalar(f.punkt, soll), 4) for f in passend}
    if len(ebenen) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{name}: {len(passend)} ebene Flächen mit Normale {list(w['normale'])} "
                                               f"in verschiedenen Ebenen um {list(w['nahe'])}")
    f = passend[0] if passend else min(innen, key=lambda x: x.abstand)
    abweichung = None if passend else (f"Normale {[round(c, 4) for c in f.normale]} statt {list(w['normale'])} "
                                       f"({winkel_grad(f.normale, soll):.3f}°)")
    return Ortung(name, "ebene", f, {"normale": tuple(round(c, 6) for c in f.normale), "punkt": f.punkt}, abweichung)


def ebene_durch_achse(name: str, achse_punkt: Vektor, achse_richtung: Vektor, nahe: Vektor) -> Ortung:
    """Ebene, die die Achse enthält und durch `nahe` geht: Normale = Achse × (nahe − Achspunkt)."""
    abstand = punkt_achse_abstand(tuple(nahe), achse_punkt, einheit(achse_richtung))
    ist = {"abstand_achse": round(abstand, 6)}
    if abstand <= ABSTAND_ACHSE_MIN:
        return Ortung(name, "ebene_durch_achse", None, ist,
                      f"nahe liegt {abstand:.3f} mm von der Achse (mindestens {ABSTAND_ACHSE_MIN:g} mm)")
    ist["normale"] = einheit(kreuz(einheit(achse_richtung), differenz(tuple(nahe), achse_punkt)))
    return Ortung(name, "ebene_durch_achse", None, ist)


def nenn_durchmesser(groesse: str) -> float:
    """"M5" → 5.0, "M10x1" → 10.0."""
    return float(groesse[1:].lower().split("x")[0])


def orte_gewinde(flaechen: list[Flaeche], gruppe: str, w: dict, tol_mm: float) -> list[Ortung]:
    """Je Position die Zylinderfläche, deren Achse durch den Eintrittspunkt läuft und parallel zu `normale` ist
    (der kleinste Radius gewinnt, wie bei Bohrungen mit Senkung); Gegenprobe Ø = Kernloch (modell kernloch) oder
    Nenn-Ø (modell nenn)."""
    n = einheit(tuple(w["normale"]))
    kern = normmasse("gewinde", w["groesse"], "ISO")["kernloch"]
    nenn = nenn_durchmesser(w["groesse"])
    ergebnis = []
    for i, p in enumerate(w["positionen"], start=1):
        name = f"{gruppe}.{i}"
        passend = [f for f in flaechen if f.art == "zylinder" and abs(abs(skalar(einheit(f.achse), n)) - 1) < 1e-6
                   and punkt_achse_abstand(tuple(p), f.punkt, einheit(f.achse)) <= tol_mm]
        if not passend:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Gewinde {name}: keine Zylinderfläche mit Achse durch {list(p)}")
        f = min(passend, key=lambda x: x.radius)
        d = 2 * f.radius
        modell = "kernloch" if abs(d - kern) <= TOL_DURCHMESSER else "nenn" if abs(d - nenn) <= TOL_DURCHMESSER else None
        abweichung = None if modell else f"Ø {d:.4f}: weder Kernloch {kern:g} noch Nenn-Ø {nenn:g} ({w['groesse']})"
        ergebnis.append(Ortung(name, "gewinde", f, {"durchmesser": round(d, 6), "modell": modell,
                                                    "achse": einheit(f.achse), "punkt": f.punkt}, abweichung))
    return ergebnis
