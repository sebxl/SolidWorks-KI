"""S18 M5: Optuna-Studie auf dem Spec-Modell der Weiche (Sortierschritt AP 6.8) – innere Schleife ohne LLM.

Stellschrauben (nur Spec-Parameter, Topologie G1c fest):
  T   Vorderkante der Trennwand (Maschine Y)  → rutsche.yaml  YV = T − R_W − R_B, R_BN = YH − 2·R_W − T
      (i.O.-Kanal 21 und Trennwand 2 bleiben, n.i.O.-Kanal nimmt den Rest bis zur Rückwand YH)
  YS  Fuß der Keilschräge, eingefahren        → weichenkeil.yaml YS
  ZF  Oberkante Fangwand und Wangen          → rutsche.yaml  ZF
Start (enqueue_trial): Stand v5 so nah wie in dieser Topologie möglich (T 193,5, YS 218,5, ZF −199).

Je Probe:
  Prüfstufe 0  swki-Schema- und Plausibilitätsprüfung der geänderten Teil-Specs (swki.spec.laden), Kollision je
               Stellung im Schnellbau (Keil ausgefahren gegen Rutsche, Keil eingefahren gegen Durchlicht) →
               trial.set_constraint; verletzt → keine Simulation
  Prüfstufe 1  N Startlagen D1 (dieselben in jeder Probe) je Bedingung, Energieprüfung wie sim.py
Ziel: max min(Anteil richtig) über die Bedingungen
  nio  v 0,10 (Keil Nennwerkstoff ABS)       io_fest v 0,05 und 0,15 mit rauem Keil µ 0,55 / e 0,55

Aufruf: .venv-sim\\Scripts\\python.exe -m spikes.s18_optuna <auftragsordner> <ausgabeordner> [--proben 90] [--n 64]
        [--kerne 15] [--minuten 80]
"""

import argparse
import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import optuna
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend, JournalFileOpenLock

from spikes import s18_sim as Q

SIM_YAML = Path(__file__).with_name("s18_sortierschritt.sim.yaml")
BEDINGUNGEN = [
    dict(name="nio_v0.10", stellung="nio", v=0.10),
    dict(name="io_v0.05_rau", stellung="io_fest", v=0.05, mu_keil=0.55, e_keil=0.55),
    dict(name="io_v0.15_rau", stellung="io_fest", v=0.15, mu_keil=0.55, e_keil=0.55),
]
DT, TC = 1e-5, 1.5e-4
BEREICH = dict(T=(176.0, 196.0), YS=(195.0, 225.0), ZF=(-199.0, -170.0))
START = dict(T=193.5, YS=218.5, ZF=-199.0)

_geladen = None


def lauf_mit(job: dict) -> dict:
    """Pool-Arbeiter: Geometrie der Probe laden (einmal je Datei), dann sim.lauf."""
    global _geladen
    pfad = job["geometrie"]
    if pfad != _geladen:
        g = json.loads(Path(pfad).read_text(encoding="utf-8"))
        Q.M.geometrie = lambda var="ist", _g=g["geometrie"]: _g
        Q.M.r_y = lambda var="ist", _r=g["r_y"]: {k: tuple(v) for k, v in _r.items()}
        for k, v in g["konstanten"].items():
            setattr(Q.M, k, v)
        Q.S._cache.clear()
        _geladen = pfad
    r = Q.S.lauf({k: v for k, v in job.items() if k != "geometrie"})
    return {k: r[k] for k in ("seed", "kerbe", "ergebnis", "sprung", "y_frei", "t_ende", "ort")}


def parameter_aus(x: dict) -> dict:
    r_w, r_b, yh = 2.0, 21.0, 218.5
    return {"rutsche.yaml": {"YV": x["T"] - r_w - r_b, "R_BN": yh - 2 * r_w - x["T"], "ZF": x["ZF"]},
            "weichenkeil.yaml": {"YS": x["YS"]}}


def pruefstufe0(ordner: Path, bg, parameter: dict) -> dict:
    """Schema/Plausibilität der geänderten Specs und Kollision je Stellung (mm³)."""
    from build123d import Location
    from spikes.s18_schnellbau import lade
    from swki.spec.laden import plausibel_befunde, schema_befunde
    befunde = []
    for datei, werte in parameter.items():
        spec = lade(ordner / datei.replace(".yaml", ".freigegeben.yaml"))
        spec = dict(spec, parameter=dict(spec["parameter"], **werte))
        b = schema_befunde(spec) or plausibel_befunde(spec, ordner)
        befunde += [f"{datei}: {x['meldung']}" for x in b]
    keil = bg.komp["weichenkeil"].bau.teil.solid
    rutsche = bg.komp["rutsche"].bau.teil.solid
    licht = bg.komp["durchlicht"].bau.teil.solid
    hub = next(g["hub"] for g in bg.gelenke() if g["id"] == "g2")
    aus = keil.moved(Location((0, 0, hub)))            # Teil +z = Maschine −Y (Weichenhub)
    def schnitt(a, b) -> float:
        s = a & b
        return 0.0 if s is None else s.volume
    k_aus, k_ein = schnitt(aus, rutsche), schnitt(keil, licht)
    return dict(befunde=befunde, kollision_aus_mm3=round(k_aus, 4), kollision_ein_mm3=round(k_ein, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ordner"); ap.add_argument("aus")
    ap.add_argument("--proben", type=int, default=90); ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--kerne", type=int, default=15); ap.add_argument("--minuten", type=float, default=80)
    ap.add_argument("--saat", type=int, default=1)
    a = ap.parse_args()
    ordner, aus = Path(a.ordner), Path(a.aus)
    aus.mkdir(parents=True, exist_ok=True)
    cache = aus / "cache"
    jobs_basis = {}
    for b in BEDINGUNGEN:
        basis = dict(stellung=b["stellung"], v=b["v"], dt=DT, tc=TC, var="spec")
        for k in ("mu_keil", "e_keil"):
            if k in b:
                basis[k] = b[k]
        jobs_basis[b["name"]] = Q.auswahl(Q.S.jobs_d1(basis), a.n)
    journal = str(aus / "studie.journal")
    storage = JournalStorage(JournalFileBackend(journal, lock_obj=JournalFileOpenLock(journal)))
    sampler = optuna.samplers.TPESampler(seed=a.saat, n_startup_trials=12)
    studie = optuna.create_study(study_name="weiche_g1c", storage=storage, direction="maximize", sampler=sampler,
                                 load_if_exists=True)
    if not studie.trials:
        studie.enqueue_trial(START)
    protokoll = aus / "proben.jsonl"
    ende = time.time() + 60 * a.minuten

    with Pool(a.kerne) as pool:
        def ziel(trial: optuna.Trial) -> float:
            t0 = time.perf_counter()
            x = {k: trial.suggest_float(k, *BEREICH[k]) for k in BEREICH}
            par = parameter_aus(x)
            geo, bg = Q.geometrie(ordner, SIM_YAML, par, cache, mit_baugruppe=True)
            t_geo = time.perf_counter() - t0
            p0 = pruefstufe0(ordner, bg, par)
            t_p0 = time.perf_counter() - t0 - t_geo
            trial.set_constraint("befunde", float(len(p0["befunde"])))
            trial.set_constraint("kollision", p0["kollision_aus_mm3"] + p0["kollision_ein_mm3"])
            zeile = dict(nr=trial.number, x=x, parameter=par, pruefstufe0=p0, t_geometrie_s=round(t_geo, 2),
                         t_pruefstufe0_s=round(t_p0, 2), zerlegung_s=geo["zeiten"]["zerlegung_s"])
            if p0["befunde"] or p0["kollision_aus_mm3"] + p0["kollision_ein_mm3"] > 1e-6:
                zeile.update(wert=0.0, verworfen=True, t_sim_s=0.0)
                wert = 0.0
            else:
                gdatei = aus / "geometrie" / f"probe_{trial.number:03d}.json"
                gdatei.parent.mkdir(exist_ok=True)
                gdatei.write_text(json.dumps(geo), encoding="utf-8")
                alle = [dict(j, geometrie=str(gdatei), bedingung=name) for name, js in jobs_basis.items() for j in js]
                t1 = time.perf_counter()
                res = pool.map(lauf_mit, [{k: v for k, v in j.items() if k != "bedingung"} for j in alle], chunksize=2)
                t_sim = time.perf_counter() - t1
                je = {}
                for j, r in zip(alle, res):
                    je.setdefault(j["bedingung"], []).append(r)
                anteile = {}
                for name, rs in je.items():
                    ok = [r for r in rs if r["sprung"] <= Q.S.SPRUNG_MAX]
                    anteile[name] = round(sum(r["ergebnis"] == "richtig" for r in ok) / max(1, len(ok)), 4)
                wert = min(anteile.values())
                zeile.update(wert=wert, anteile=anteile, t_sim_s=round(t_sim, 1), laeufe=len(res))
                gdatei.unlink()
            zeile["t_probe_s"] = round(time.perf_counter() - t0, 1)
            with protokoll.open("a", encoding="utf-8") as f:
                f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
            print(json.dumps({k: zeile[k] for k in ("nr", "x", "wert", "t_probe_s") if k in zeile}
                             | {"anteile": zeile.get("anteile"), "verworfen": zeile.get("verworfen", False)},
                             ensure_ascii=False), flush=True)
            return wert

        t_start = time.perf_counter()
        while len(studie.trials) < a.proben and time.time() < ende:
            studie.optimize(ziel, n_trials=1)
        dauer = time.perf_counter() - t_start
    best = studie.best_trial
    zf = dict(proben=len(studie.trials), dauer_min=round(dauer / 60, 1), proben_je_stunde=round(len(studie.trials) / dauer * 3600, 1),
              bester=dict(nr=best.number, wert=best.value, x=best.params),
              erste_ueber_99=next((t.number for t in studie.trials if t.value is not None and t.value >= 0.99), None))
    (aus / "zusammenfassung.json").write_text(json.dumps(zf, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(zf, ensure_ascii=False))


if __name__ == "__main__":
    main()
