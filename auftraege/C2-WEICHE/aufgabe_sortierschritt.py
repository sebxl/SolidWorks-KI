"""Prüfaufgabe Sortierschritt der Prüfstation AP 6.8 (Zielfunktions-Baustein für swki optimiere, Spec C2 §3).

Schieber Pos. 1 → Pos. 3 schiebt das Messer über die Abgabekante in die Weiche: landet es im richtigen Schacht?
Ablauf, Werkstoffe, Startlagen D1 und Auswertung sind unverändert die der Studie sortierschritt-2026-10-18 (sim.py,
modell.py, ablauf.py; nur gelesen, wie Spike S-Schleife-1 `spikes/s18_sim.py`). Ersetzt werden die Körper
(modell.geometrie) und die Lage der Rutschenkanäle (modell.r_y, R_XI0, R_RS, R_ZO, R_ZU) – beides aus der Probe, also
aus den Specs. Fehlschläge werden klassifiziert (Fehlerbilder), Läufe mit Energiezuwachs sind ungültig.

Pfad der Studie: config/rechner.yaml `dateien: {sortierschritt_skripte: …}`, sonst der Hauptcheckout.
Teil-/Baugruppenkoordinaten (x, y, z) → Maschine (X, Y, Z) = (x, −z, y) (pruefstation.yaml Kopf).
"""

import math
import sys
from pathlib import Path

import numpy as np


def _skripte() -> Path:
    try:
        from swki.konfig import lade_rechner
        p = lade_rechner().dateien.get("sortierschritt_skripte")
        if p:
            return Path(p)
    except Exception:
        pass
    return Path(r"C:\Users\User\Documents\Projekte\SolidWorks-KI\auftraege\AP68-Pruefstation\simulation"
                r"\sortierschritt-2026-10-18\skripte")


SKRIPTE = _skripte()
if str(SKRIPTE) not in sys.path:
    sys.path.insert(0, str(SKRIPTE))
import modell as M  # noqa: E402
import sim as S  # noqa: E402

VS = SKRIPTE.parent.parent / "v-schieber-2026-10-16" / "skripte"
ABHAENGIGKEITEN = [str(SKRIPTE / "sim.py"), str(SKRIPTE / "modell.py"), str(SKRIPTE / "ablauf.py"),
                   str(VS / "messer.py"), str(VS / "modell.py"), str(Path(S.D1_DATEI).resolve())]
DT, TC = 1e-5, 1.5e-4                        # wie Spike M4/M5
TAN60 = math.tan(math.radians(60))
_geladen = None
_alle_d1 = None


def maschine(p) -> np.ndarray:
    p = np.asarray(p, float)
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def rutsche_y(r: dict) -> dict:
    """Y-Grenzen der Kanäle und Wände aus den Rutschen-Parametern (rutsche.yaml: T = Vorderkante Trennwand)."""
    t, rw, rb, yh = r["T"], r["R_W"], r["R_B"], r["YH"]
    yv, rbn = t - rw - rb, yh - 2 * rw - t
    return dict(vorn=(yv, yv + rw), io=(yv + rw, yv + rw + rb), trenn=(yv + rw + rb, yh - rw - rbn),
                nio=(yh - rw - rbn, yh - rw), hinten=(yh - rw, yh))


def _teil_der_rutsche(c: np.ndarray, ry: dict, zo: float) -> str:
    """Name eines Rutschenstücks nach seiner Lage (für Fehlerbilder: an welcher Wand?)."""
    if c[2] > zo + 0.5:
        return "fang"
    for name in ("vorn", "trenn", "hinten"):
        if ry[name][0] - 0.01 <= c[1] <= ry[name][1] + 0.01:
            return name
    return "seite" if c[2] > zo - 130 else "lasche"


def _lade(probe: dict) -> None:
    """Geometrie der Probe in das Modell der Studie setzen (je Arbeitsprozess einmal je Probe)."""
    global _geladen
    if _geladen == id(probe):
        return
    sim = probe["simulation"]
    r = probe["parameter"]["rutsche.yaml"]
    ry = rutsche_y(r)
    koerper_von = {}
    for gid, g in sim["gelenke"].items():
        gl = next(x for x in probe["gelenke"] if x["id"] == gid)
        achse = maschine([gl["achse"]])[0]
        hub = gl["bereich"][1]
        soll = {"schieber": M.HUB3, "keil": M.W_HUB}[g["koerper"]]          # Hub des Ablaufs (ablauf.py)
        if abs(hub - soll) > 1e-9 or np.abs(achse - (0, -1, 0)).max() > 1e-9:
            raise ValueError(f"Gelenk {gid}: Achse {achse.tolist()} Hub {hub} – der Ablauf erwartet −Y und {soll}")
        koerper_von[gl["komponente"]] = g["koerper"]
    geo = []
    for kid, stuecke in probe["stuecke"].items():
        e = sim["komponenten"][kid]
        koerper = koerper_von.get(probe["koerper"][kid], "welt")
        for i, pts in enumerate(stuecke):
            p = maschine(pts)
            name = e["name"]
            if kid == "rutsche":
                name = f"rutsche_{_teil_der_rutsche(p.mean(axis=0), ry, r['ZO'])}_"
            geo.append(dict(name=f"{name}{i}", art="mesh", daten=[round(float(c), 6) for c in p.ravel()],
                            material=e["material"], koerper=koerper, gruppe=koerper if koerper != "welt" else e["name"],
                            stoss=True))
    M.geometrie = lambda var="ist", _g=geo: _g
    M.r_y = lambda var="ist", _r=ry: dict(_r)
    M.R_XI0, M.R_RS, M.R_ZO = r["XI0"], r["RS"], r["ZO"]
    M.R_ZU = r["ZO"] - r["DX"] * TAN60
    S._cache.clear()
    _geladen = id(probe)


def jobs(szenario: dict, n: int, saat: int, erster: int = 0) -> list[dict]:
    """Startlagen D1 (1992) in fester, je Szenario gemischter Reihenfolge; Läufe erster … erster+n−1."""
    global _alle_d1
    werte = dict(szenario.get("werte", {}))
    basis = dict(stellung=werte.pop("stellung"), var="spec", dt=DT, tc=TC, **werte)
    if _alle_d1 is None:
        _alle_d1 = S.jobs_d1({})
    folge = np.random.default_rng(saat).permutation(len(_alle_d1))
    out = []
    for k in folge[erster:erster + n]:
        j = {key: v for key, v in _alle_d1[int(k)].items()}
        out.append(dict(j, **basis))
    return out


def _partner(r: dict, bis: float | None) -> str | None:
    """Letzter Kontaktpartner des Messers bis zur Zeit bis (Gruppe ohne laufende Nummer)."""
    kand = [(t, p) for p, t in (r.get("zuletzt") or {}).items() if bis is None or t <= bis + 1e-9]
    if not kand:
        return None
    p = max(kand)[1]
    return p.rstrip("0123456789").rstrip("_")


def fehlerbild(r: dict, ry: dict) -> str | None:
    e = r["ergebnis"]
    if e == "richtig":
        return None
    nach = " (Schieber trifft erneut)" if r.get("schieber_flug") else ""
    if e == "falsch":
        ein, ende = r.get("schacht_ein"), r.get("schacht_ende")
        if ein in ("io", "nio") and ende in ("io", "nio") and ein != ende:
            return f"Sprung über die Trennwand ({ein}→{ende}){nach}"
        y = r.get("y_frei")
        if y is not None and ry["trenn"][0] - 2 <= y <= ry["trenn"][1] + 2:
            return f"Treffer auf die Trennwandkante (freier Landepunkt Y {y:.0f}){nach}"
        p = _partner(r, r.get("t_ein"))
        if p == "keil":
            return f"Abprall am Keil in den falschen Kanal{nach}"
        return f"Flugbahn in den falschen Kanal (zuletzt {p or '–'}){nach}"
    if e == "daneben":
        return f"daneben: {r.get('ort')} nach Kontakt mit {_partner(r, None) or '–'}{nach}"
    return f"{e}: {r.get('ort')}{nach}"


def lauf(probe: dict, job: dict) -> dict:
    _lade(probe)
    g = probe.get("genauigkeit", {})
    j = dict(job, dt=job.get("dt", DT) * g.get("zeitschritt_faktor", 1.0),
             tc=job.get("tc", TC) * g.get("kontakt_faktor", 1.0))
    r = S.lauf(j)
    ry = M.r_y()
    y = r.get("y_frei")
    abstand = None
    if y is not None:
        lo, hi = ry["trenn"]
        abstand = 0.0 if lo <= y <= hi else min(abs(y - lo), abs(y - hi))
    return {"ergebnis": r["ergebnis"], "fehlerbild": fehlerbild(r, ry), "gueltig": r["sprung"] <= S.SPRUNG_MAX,
            "y_frei": y, "abstand_trennwand_mm": abstand, "ort": r.get("ort"), "seed": r.get("seed")}


def kennzahlen(laeufe: dict) -> dict:
    """Abstand des freien Landepunkts zur Trennwand (5-%-Quantil über alle gültigen Läufe, mm)."""
    a = sorted(x["abstand_trennwand_mm"] for ls in laeufe.values() for x in ls
               if x.get("gueltig", True) and x.get("abstand_trennwand_mm") is not None)
    return {"abstand_trennwand_p05_mm": a[int(0.05 * (len(a) - 1))] if a else None}

