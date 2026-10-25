"""S18 M4: Sortierschritt AP 6.8 mit Geometrie aus den Specs (Schnellbau + Zerlegung) statt aus dem Handmodell.

Ablauf, Werkstoffe, Startlagen und Auswertung sind unverändert die der Studie simulation/sortierschritt-2026-10-18
(skripte/sim.py, modell.py, ablauf.py – nur gelesen). Ersetzt werden modell.geometrie (Körper) und die Lage der
Rutschenkanäle für die Auswertung (modell.r_y, R_XI0, R_RS, R_ZO, R_ZU) – beides aus der Spec.

Ablauf:
  geometrie   baut die Simulationsgeometrie aus Baugruppen- und Teil-Specs, prüft Gelenke gegen den Ablauf der
              Prüfaufgabe (Achse −Y, Hub 82 bzw. 25) und schreibt sie als JSON (Hauptprozess, mit Cache)
  lauf        rechnet die Fälle wie sim.py (Pool, Geometrie über S18_GEOMETRIE in jedem Prozess)

Aufruf: .venv-sim\\Scripts\\python.exe -m spikes.s18_sim <auftragsordner> <sim.yaml> <stellung> <ausgabe.json>
        [--var G1c] [--parameter rutsche.yaml:R_BN=35 ...] [--n 200] [--kerne 15]
Umgebung wie sim.py (V, DT, TC, MU_KEIL, E_KEIL, …).
"""

import json
import math
import os
import sys
import time
from pathlib import Path

SKRIPTE = Path(os.environ.get("S18_SKRIPTE", r"C:\Users\User\Documents\Projekte\SolidWorks-KI\auftraege"
                               r"\AP68-Pruefstation\simulation\sortierschritt-2026-10-18\skripte"))
if str(SKRIPTE) not in sys.path:
    sys.path.insert(0, str(SKRIPTE))
import modell as M  # noqa: E402

_GEOMETRIE = os.environ.get("S18_GEOMETRIE")
if _GEOMETRIE:
    _G = json.loads(Path(_GEOMETRIE).read_text(encoding="utf-8"))
    M.geometrie = lambda var="ist": _G["geometrie"]
    M.r_y = lambda var="ist": {k: tuple(v) for k, v in _G["r_y"].items()}
    for _k, _v in _G["konstanten"].items():
        setattr(M, _k, _v)
import sim as S  # noqa: E402


def geometrie(ordner: Path, sim_yaml: Path, parameter: dict | None = None, cache: Path | None = None,
              ohne: dict | None = None, mit_baugruppe: bool = False):
    from spikes.s18_baugruppe import Baugruppe, lade_sim
    cfg = lade_sim(sim_yaml)
    t0 = time.perf_counter()
    bg = Baugruppe(ordner, cfg["baugruppe"], list(cfg["komponenten"]) + list(cfg.get("nur_lage", [])), parameter,
                   ohne=ohne)
    t_bau = time.perf_counter() - t0
    bg.loese_lage()
    gelenke = {g["id"]: g for g in bg.gelenke()}
    t1 = time.perf_counter()
    st = bg.stuecke(cfg.get("zerlegung_toleranz_mm", 0.01), cache, nur=list(cfg["komponenten"]))
    t_zerl = time.perf_counter() - t1
    koerper = {}
    for gid, g in cfg["gelenke"].items():
        j = gelenke[gid]
        for k in j["komponenten"]:
            koerper[k] = g["koerper"]
    pruef = {}
    for gid, soll in (("g1", M.HUB3), ("g2", M.W_HUB)):     # Ablauf der Prüfaufgabe: Schub −Y, Hub 82 / 25
        j = gelenke[gid]
        pruef[gid] = dict(achse=j["achse_maschine"], hub=j["hub"], soll_hub=soll,
                          ok=abs(j["hub"] - soll) < 1e-9 and max(abs(a - b) for a, b in zip(j["achse_maschine"], (0, -1, 0))) < 1e-9)
    geo = []
    for kid, eintrag in cfg["komponenten"].items():
        for i, pts in enumerate(st["stuecke"][kid]):
            geo.append(dict(name=f"{eintrag['name']}{i}", art="mesh", daten=[round(float(c), 6) for c in pts.ravel()],
                            material=eintrag["material"], koerper=koerper.get(kid, "welt"),
                            gruppe=koerper.get(kid, eintrag["name"]), stoss=True))
    r = bg.komp["rutsche"].bau.p
    yv, yh, rw, rb, rbn = r["YV"], r["YH"], r["R_W"], r["R_B"], r["R_BN"]
    r_y = dict(vorn=(yv, yv + rw), io=(yv + rw, yv + rw + rb), trenn=(yv + rw + rb, yh - rw - rbn),
               nio=(yh - rw - rbn, yh - rw), hinten=(yh - rw, yh))
    konst = dict(R_XI0=r["XI0"], R_RS=r["RS"], R_ZO=r["ZO"], R_ZU=r["ZO"] - r["DX"] * math.tan(math.radians(60)))
    erg = dict(geometrie=geo, r_y=r_y, konstanten=konst, gelenke=pruef, lage={k: c.t for k, c in bg.komp.items()},
                meldungen=bg.meldungen, zerlegung=st["berichte"],
                zeiten=dict(schnellbau_s=round(t_bau, 3), zerlegung_s=round(t_zerl, 3),
                            je_teil_bau_s={k: round(v, 4) for k, v in bg.zeiten.items()},
                            je_teil_zerlegung_s={k: round(v, 4) for k, v in st["zeiten"].items()}),
                stuecke=len(geo))
    return (erg, bg) if mit_baugruppe else erg


def basis_aus_umgebung(stellung: str, var: str | None) -> dict:
    basis = dict(stellung=stellung)
    if var:
        basis["var"] = var
    for env, key in (("V", "v"), ("MU_STIRN", "mu_stirn"), ("MU_ABS", "mu_abs"), ("E_ABS", "e_abs"),
                     ("T_REAKTION", "t_reaktion"), ("T_ANLAUF", "t_anlauf"), ("V_KEIL", "v_keil"),
                     ("S_6BG3", "s_6bg3"), ("V_RUECK", "v_rueck"), ("MU_GLAS", "mu_glas"), ("MU_BODEN", "mu_boden"),
                     ("DT", "dt"), ("TC", "tc"), ("MU_KEIL", "mu_keil"), ("E_KEIL", "e_keil")):
        if env in os.environ:
            basis[key] = float(os.environ[env])
    return basis


def rechne(jobs: list, kerne: int) -> list:
    from multiprocessing import Pool
    with Pool(kerne) as p:
        return p.map(S.lauf, jobs, chunksize=2)


def auswahl(jobs: list, n: int | None) -> list:
    if not n:
        return jobs
    return jobs[::max(1, len(jobs) // n)][:n]


def zusammenfassung(res: list) -> dict:
    from collections import Counter
    ok = [r for r in res if r["sprung"] <= S.SPRUNG_MAX]
    c = Counter(r["ergebnis"] for r in ok)
    return dict(n=len(res), gueltig=len(ok), ergebnis=dict(c), richtig=round(c.get("richtig", 0) / max(1, len(ok)), 5),
                y_frei_median=_median([r["y_frei"] for r in ok if r["y_frei"] is not None]))


def _median(x):
    x = sorted(x)
    return None if not x else (x[len(x) // 2] if len(x) % 2 else (x[len(x) // 2 - 1] + x[len(x) // 2]) / 2)


def _parameter(args: list) -> dict:
    out = {}
    for a in args:
        datei, _, zuw = a.partition(":")
        name, _, wert = zuw.partition("=")
        out.setdefault(datei, {})[name] = float(wert)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("ordner"); ap.add_argument("sim_yaml"); ap.add_argument("stellung"); ap.add_argument("ausgabe")
    ap.add_argument("--var", default="G1c"); ap.add_argument("--parameter", nargs="*", default=[])
    ap.add_argument("--ohne", nargs="*", default=[], help="datei:feature1,feature2 – Features weglassen")
    ap.add_argument("--n", type=int); ap.add_argument("--kerne", type=int, default=15)
    ap.add_argument("--hand", action="store_true", help="Handmodell rechnen (Vergleich), keine Spec-Geometrie")
    ap.add_argument("--cache", default=r"C:\Users\User\.swki\arbeit\SPIKES\s18\cache")
    a = ap.parse_args()
    aus = Path(a.ausgabe)
    meta = {}
    if not a.hand:
        ohne = {d: f.split(",") for d, _, f in (x.partition(":") for x in a.ohne)}
        g = geometrie(Path(a.ordner), Path(a.sim_yaml), _parameter(a.parameter), Path(a.cache), ohne)
        gdatei = aus.with_suffix(".geometrie.json")
        gdatei.write_text(json.dumps(g), encoding="utf-8")
        os.environ["S18_GEOMETRIE"] = str(gdatei)
        meta = {k: g[k] for k in ("gelenke", "lage", "meldungen", "zerlegung", "zeiten", "stuecke")}
        print(json.dumps({k: meta[k] for k in ("gelenke", "zeiten", "stuecke", "meldungen")}, ensure_ascii=False))
    jobs = auswahl(S.jobs_d1(basis_aus_umgebung(a.stellung, a.var)), a.n)
    t0 = time.perf_counter()
    res = rechne(jobs, a.kerne)
    dauer = time.perf_counter() - t0
    zf = zusammenfassung(res)
    zf.update(sim_s=round(dauer, 1), je_lauf_cpu_s=round(dauer * a.kerne / len(res), 3), modell="hand" if a.hand else "spec")
    print(json.dumps(zf, ensure_ascii=False))
    aus.write_text(json.dumps(dict(zusammenfassung=zf, meta=meta, laeufe=res), separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
