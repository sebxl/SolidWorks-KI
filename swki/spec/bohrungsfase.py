"""Fase am Bohrungseintritt (Feld `fase` an bohrung/normbohrung, Paket Konstruktionsstil): Fasenabstand und Radius der
Eintrittskante in mm, ohne SolidWorks. Genutzt von Compiler (Feature <id>_fase), volumen: auto und Gewindeprüfung."""

import re

from swki.spec.ausdruck import auswerten
from swki.spec.normen import norm_von, normmasse


def nenn_durchmesser(groesse) -> float:
    """Gewinde-Nenn-Ø aus der Größe ("M8", "M10x1" → 8, 10)."""
    treffer = re.match(r"M(\d+(?:\.\d+)?)", str(groesse))
    if treffer is None:
        raise ValueError(f"keine Gewindegröße: {groesse!r}")
    return float(treffer.group(1))


def eintritt_radius(f: dict, parameter: dict) -> float:
    """Radius der Kante, auf der die Fase sitzt: Kernloch (Gewinde), Senkung (Zylinderschraube, Bohrung mit Senkung),
    sonst die Bohrung bzw. das Stiftloch."""
    if f["typ"] == "bohrung":
        d = f["senkung"]["durchmesser"] if "senkung" in f else f["durchmesser"]
        return auswerten(d, parameter) / 2
    m = normmasse(f["art"], f["groesse"], norm_von(f))
    schluessel = {"gewinde": "kernloch", "zylinderschraube": "senkung_d", "stift": "durchmesser"}[f["art"]]
    return m[schluessel] / 2


def fase_abstand(f: dict, parameter: dict) -> float | None:
    """Abstand c der Fase c × 45° in mm; `nenn` = (Nenn-Ø − Kernloch-Ø)/2 (Ansenkung auf Nenn-Ø); None ohne Feld."""
    if "fase" not in f:
        return None
    if f["fase"] == "nenn":
        return (nenn_durchmesser(f["groesse"]) - 2 * eintritt_radius(f, parameter)) / 2
    return auswerten(f["fase"], parameter)
