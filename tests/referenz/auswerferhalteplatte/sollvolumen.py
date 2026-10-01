"""Analytisches Sollvolumen der Referenz Auswerferhalteplatte (Stufe 2c) aus Parametern und Maßtabelle.

Aufruf: .venv\\Scripts\\python.exe tests\\referenz\\auswerferhalteplatte\\sollvolumen.py
Rechnet unabhängig vom Compiler und von swki.pruefung.geometrie; nur die Normmaße kommen aus
swki/wissen/bohrungsnormen.yaml (live gemessen in Spike S10). Das Ergebnis gehört nach pruefung.volumen.soll in
auswerferhalteplatte.yaml (samt Kommentar) – nie ein Messwert.
"""

import math
import sys
from pathlib import Path

import yaml

from swki.spec.normen import bohrspitze_grad, normmasse

SPEC = Path(__file__).with_name("auswerferhalteplatte.yaml")


def _bohrung(art: str, groesse, tiefe: float | None, dicke: float) -> float:
    """Eine Normbohrung: zylindrischer Teil ab der Fläche (blind mit Bohrspitze), Senkung von der Fläche aus."""
    m = normmasse(art, groesse)
    d = m.get("kernloch") or m.get("durchgang") or m["durchmesser"]
    v = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        v += math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(bohrspitze_grad()) / 2)
    if art == "zylinderschraube":
        v += math.pi * (m["senkung_d"] ** 2 - d**2) / 4 * m["senkung_t"]
    elif art == "senkschraube":
        ds = m["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(m["senkwinkel"]) / 2)
        v += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return v


def rechnung() -> dict[str, float]:
    p = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["parameter"]
    L, B, H, R, F, RW = (p[k] for k in ("L", "B", "H", "R", "F", "RW"))
    return {
        "Platte (L·B − (4 − π)·R²)·H": (L * B - (4 - math.pi) * R**2) * H,
        "− Fase F²/2 · (2(L − 2R) + 2(B − 2R) + 2π(R − F/3))":
            -F**2 / 2 * (2 * (L - 2 * R) + 2 * (B - 2 * R) + 2 * math.pi * (R - F / 3)),
        "− Tasche f7 (TL·TB − (4 − π)·TR²)·(H − RW)": -(p["TL"] * p["TB"] - (4 - math.pi) * p["TR"] ** 2) * (H - RW),
        "− Langloch f8 (LL·LB + π·LB²/4)·RW": -(p["LL"] * p["LB"] + math.pi * p["LB"] ** 2 / 4) * RW,
        "− Aussparung f9 (KB·KH + π·(KH/2)²)·KT": -(p["KB"] * p["KH"] + math.pi * (p["KH"] / 2) ** 2) * p["KT"],
        "− f2 4 × ISO 4762 M8 durch": -4 * _bohrung("zylinderschraube", "M8", None, H),
        "− f3 2 × Stift Ø8 durch": -2 * _bohrung("stift", 8, None, H),
        "− f4 2 × M10, Bohrtiefe BT": -2 * _bohrung("gewinde", "M10", p["BT"], H),
        "− f5 1 × M12x1,5 durch": -_bohrung("gewinde", "M12x1.5", None, H),
        "− f6 2 × ISO 10642 M6 durch": -2 * _bohrung("senkschraube", "M6", None, H),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Konsole unter cp1252: sonst brechen "³", "π" und "−" die Ausgabe ab
    teile = rechnung()
    for text, wert in teile.items():
        print(f"{wert:14.3f}  {text}")
    print(f"{sum(teile.values()):14.3f}  Sollvolumen mm³")
