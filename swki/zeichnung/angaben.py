"""Zeichnungsableitung Z1.3 Stufe 3: Angabetexte (Bohrungsangaben) und Bohrbilder aus der Spec, ohne SolidWorks."""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from swki.spec.ausdruck import auswerten

FASE_SUFFIX = " × 45°"
_NORMEN = Path(__file__).parents[1] / "wissen" / "bohrungsnormen.yaml"


@dataclass(frozen=True)
class Bohrbild:
    merkmal: str
    anzahl: int
    teilkreis: float | None
    teilung: float | None
    reihe: str | None
    reihe_anzahl: int | None = None


def zahl(x: float) -> str:
    """Dezimalkomma, ohne nachgestellte Nullen."""
    text = f"{round(float(x), 4):.4f}".rstrip("0").rstrip(".")
    return (text or "0").replace(".", ",")


@lru_cache(maxsize=1)
def _normen() -> dict:
    return yaml.safe_load(_NORMEN.read_text(encoding="utf-8"))["normen"]["ISO"]


def _enthalten(spec: dict, fid: str) -> list[dict]:
    """Alle muster_*/spiegeln, die das Feature direkt oder über ein anderes Muster enthalten (innen nach außen)."""
    gefunden: list[dict] = []
    ids = {fid}
    neu = True
    while neu:
        neu = False
        for f in spec.get("features", []):
            if f.get("typ") in ("muster_linear", "muster_kreis", "spiegeln") and f not in gefunden \
                    and ids & set(f.get("features", [])):
                gefunden.append(f)
                ids.add(f["id"])
                neu = True
    return gefunden


def bohrbilder(spec: dict) -> dict[str, Bohrbild]:
    param = spec.get("parameter", {})
    bilder = {}
    for f in spec.get("features", []):
        if f.get("typ") not in ("bohrung", "normbohrung"):
            continue
        positionen = f.get("positionen") or [[0, 0]]
        anzahl, teilkreis, teilung, reihe, reihe_n = len(positionen), None, None, None, None
        for m in _enthalten(spec, f["id"]):
            if m["typ"] == "spiegeln":
                anzahl *= 2
            elif m["typ"] == "muster_kreis":
                anzahl *= int(auswerten(m["anzahl"], param))
                if teilkreis is None and f.get("positionen"):
                    try:
                        u, v = (auswerten(c, param) for c in positionen[0][:2])
                        teilkreis = round(2 * math.hypot(u, v), 6)
                    except (ValueError, TypeError, KeyError):
                        teilkreis = None
            else:
                r1, r2 = m["richtung1"], m.get("richtung2")
                anzahl *= int(auswerten(r1["anzahl"], param)) * (int(auswerten(r2["anzahl"], param)) if r2 else 1)
                if r2 is None and teilung is None and len(positionen) == 1:
                    teilung, reihe = float(auswerten(r1["abstand"], param)), m["id"]
                    reihe_n = int(auswerten(r1["anzahl"], param))
        bilder[f["id"]] = Bohrbild(f["id"], anzahl, teilkreis, teilung, reihe, reihe_n)
    return bilder


def reihenzusatz(bild: Bohrbild) -> tuple[str, str]:
    """Präfix und Suffix für das Teilungsmaß einer Reihe, z. B. ("4 × ", " (= 120)")."""
    n = (bild.reihe_anzahl or bild.anzahl) - 1
    return f"{n} × ", f" (= {zahl(n * (bild.teilung or 0))})"


def _nenn(groesse: str) -> str:
    m = re.match(r"M(\d+(?:\.\d+)?)", groesse)
    return zahl(float(m.group(1))) if m else groesse


def bohrungsangabe(feature: dict, spec: dict, bild: Bohrbild) -> tuple[str, list[str]]:
    """(Text mit Zeilenumbrüchen, Meldungen) der Bohrungsangabe."""
    param = spec.get("parameter", {})
    meld: list[str] = []
    fid, art, groesse = feature["id"], feature.get("art"), str(feature.get("groesse", ""))
    zeilen: list[str] = []
    if feature["typ"] == "normbohrung":
        tab = _normen().get(art, {}).get(groesse)
        if tab is None:
            meld.append(f"ANGABE_UNBEKANNT: {fid} {art} {groesse} nicht in bohrungsnormen.yaml")
        if art == "gewinde":
            kopf = groesse
            tiefe = feature.get("gewindetiefe", feature.get("tiefe"))
        elif art == "stift":
            kopf = f"Ø{zahl(float(groesse))}" if re.fullmatch(r"[\d.]+", groesse) else groesse
            tiefe = feature.get("tiefe")
        else:
            kopf = f"Ø{zahl(tab['durchgang'])}" if tab else groesse
            tiefe = feature.get("tiefe")
            if tab and art == "zylinderschraube":
                zeilen.append(f"Senkung Ø{zahl(tab['senkung_d'])} × {zahl(tab['senkung_t'])} tief")
            elif tab and art == "senkschraube":
                zeilen.append(f"Senkung Ø{zahl(tab['senkung_d'])} × {zahl(tab.get('senkwinkel', 90))}°")
    else:
        kopf, tiefe = f"Ø{zahl(auswerten(feature['durchmesser'], param))}", feature.get("tiefe")
    if feature.get("durch"):
        tief = "durch"
    elif tiefe is not None:
        tief = f"{zahl(auswerten(tiefe, param))} tief"
    else:
        tief = ""
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} Tiefe fehlt (weder durch noch tiefe/gewindetiefe)")
    kopfzeile = f"{bild.anzahl} × {kopf}" + (f" – {tief}" if tief else "")
    fase = feature.get("fase")
    if fase == "nenn" and art == "gewinde":
        zeilen.append(f"Senkung Ø{_nenn(groesse)} × 90°")
    elif fase == "nenn":
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} fase nenn bei Art {art} nicht ausgegeben")
    elif fase is not None:
        zeilen.append(f"Fase {zahl(auswerten(fase, param))}{FASE_SUFFIX}")
    if bild.teilkreis is not None:
        zeilen.append(f"TK Ø{zahl(bild.teilkreis)}")
    elif any(m["typ"] == "muster_kreis" for m in _enthalten(spec, fid)):
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} Teilkreis nicht bestimmbar (Position fehlt oder unlesbar)")
    return "\n".join([kopfzeile, *zeilen]), meld
