"""Kleiner Optimierungsauftrag für Tests (selbst formuliert): Rampe mit einstellbarer Neigung, auf der ein Klotz
rutscht. Die Prüfaufgabe `aufgabe_rampe.py` rechnet ohne MuJoCo (Reibung gegen Hangabtrieb, Streuung des Reibwerts), damit
der Runner in Sekunden testbar ist; `aufgabe_mujoco.py` lässt einen Würfel wirklich fallen."""

import copy
from pathlib import Path

import yaml

RAMPE = {
    "art": "teil",
    "name": "Rampe",
    "material": "1.0037",
    "parameter": {"L": 100, "B": 40, "H": 30, "W": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"polygon": {"punkte": [[0, 0], ["=L", 0], [0, "=H"]]}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
    ],
    "optimierung": {
        "variante": "Rampe glatt",
        "pruefaufgabe": {"modul": "aufgabe_rampe.py"},
        "ziel": {"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 0.95},
        "stellschrauben": [
            {"name": "H", "parameter": "H", "rahmen": [5, 80], "bereich": [5, 40]},
            {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 1.0]},
        ],
        "szenarien": [
            {"name": "trocken", "laeufe": 24, "werte": {"mu": 0.4}, "streuung": {"mu": [0.3, 0.5]}},
            {"name": "geoelt", "laeufe": 24, "werte": {"mu": 0.2}},
        ],
        "budget": {"proben": 40, "minuten": 5},
        "plateau": {"proben": 8, "epsilon": 0.01},
        "automatik": {"bereich_erweitern": True, "sampler": ["tpe", "zufall"], "mehrfachstart": 2},
        "start": [{"H": 10, "v0": 0.0}],
        "erlaubte_formaenderungen": [],
    },
}

AUFGABE_RAMPE = '''"""Test-Prüfaufgabe: rutscht der Klotz die Rampe hinunter? (ohne MuJoCo)"""
import math, random

def jobs(szenario, n, saat, erster=0):
    out = []
    for i in range(erster, erster + n):
        r = random.Random(saat * 100003 + i)
        j = dict(szenario.get("werte", {}), nr=i)
        for k, (lo, hi) in szenario.get("streuung", {}).items():
            j[k] = lo + (hi - lo) * r.random()
        out.append(j)
    return out

def lauf(probe, job):
    p = probe["parameter"]["rampe.yaml"]
    neigung = math.atan2(p["H"], p["L"])
    ueber = math.tan(neigung) - job["mu"] + job.get("v0", 0.0) * 0.3
    if ueber > 0.05:
        return {"ergebnis": "richtig", "gueltig": True, "ueber": ueber}
    return {"ergebnis": "liegt", "fehlerbild": "haftet auf der Rampe" if ueber < 0 else "kriecht",
            "gueltig": job["nr"] % 23 != 22, "ueber": ueber}

def kennzahlen(laeufe):
    alle = [r["ueber"] for rs in laeufe.values() for r in rs]
    return {"min_ueber": min(alle)}
'''


def lege_an(ordner: Path, spec: dict | None = None, aufgabe: str = AUFGABE_RAMPE) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / "rampe.yaml"
    pfad.write_text(yaml.safe_dump(spec or copy.deepcopy(RAMPE), allow_unicode=True, sort_keys=False), encoding="utf-8")
    (ordner / "aufgabe_rampe.py").write_text(aufgabe, encoding="utf-8")
    return pfad


def rampe(**opt) -> dict:
    spec = copy.deepcopy(RAMPE)
    spec["optimierung"].update(opt)
    return spec
