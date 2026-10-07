"""Analytisches Sollvolumen der Referenz Zentrieraufnahme (Paket Formschräge) aus den Parametern.

Aufruf: .venv\\Scripts\\python.exe tests\\referenz\\zentrieraufnahme\\sollvolumen.py
Rechnet unabhängig vom Compiler und von swki.formschraege/swki.pruefung.geometrie (Kegelstümpfe und das Integral des
versetzten Querschnitts je Element). Das Ergebnis gehört nach pruefung.volumen.soll in zentrieraufnahme.yaml (samt
Kommentar) – nie ein Messwert.
"""

import math
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).with_name("zentrieraufnahme.yaml")


def _kegelstumpf(r1: float, r2: float, h: float) -> float:
    return math.pi * h / 3 * (r1 * r1 + r1 * r2 + r2 * r2)


def _integral(flaeche, tiefe: float) -> float:
    """∫₀^tiefe flaeche(h) dh mit der Simpsonregel – exakt, weil flaeche(h) ein Polynom höchstens 2. Grades ist."""
    return tiefe / 6 * (flaeche(0) + 4 * flaeche(tiefe / 2) + flaeche(tiefe))


def rechnung() -> dict[str, float]:
    p = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["parameter"]
    t = {k: math.tan(math.radians(p[k])) for k in ("WZ", "WT", "WR", "WS")}
    zapfen_r1 = p["DZ"] / 2
    trichter_r1 = p["DR"] / 2

    def tasche(h: float) -> float:  # Rechteck mit Eckradius, um d = h·tan WT nach innen versetzt
        d = h * t["WT"]
        return (p["TL"] - 2 * d) * (p["TB"] - 2 * d) - (4 - math.pi) * (p["TR"] - d) ** 2

    def steg_ueber_platte(h: float) -> float:  # Steg im Abstand h von der Ebene vorne, nur der Teil über y = H
        d = h * t["WS"]
        return (p["SL"] - 2 * d) * (p["SY"] + p["SH"] / 2 - d - p["H"])

    return {
        "Platte (L·B − (4 − π)·R²)·H": (p["L"] * p["B"] - (4 - math.pi) * p["R"] ** 2) * p["H"],
        "+ Zapfen, Kegelstumpf Ø DZ → DZ − 2·HZ·tan WZ": _kegelstumpf(zapfen_r1, zapfen_r1 - p["HZ"] * t["WZ"], p["HZ"]),
        "+ Steg über der Platte, 2 × ∫ (SL − 2d)·(SY + SH/2 − d − H)": 2 * _integral(steg_ueber_platte, p["ST"] / 2),
        "− Tasche, ∫ Rechteck mit Eckradius nach innen versetzt": -_integral(tasche, p["TT"]),
        "− Trichter, Kegelstumpf Ø DR → DR + 2·H·tan WR": -_kegelstumpf(trichter_r1, trichter_r1 + p["H"] * t["WR"], p["H"]),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Konsole unter cp1252: sonst brechen "³", "π" und "−" die Ausgabe ab
    teile = rechnung()
    for text, wert in teile.items():
        print(f"{wert:14.3f}  {text}")
    print(f"{sum(teile.values()):14.3f}  Sollvolumen mm³")
