"""Innere Schleife ohne Claude (Spec C2 §4): Optuna (ask/tell, JournalStorage) über Schnellbau und Prüfaufgabe.

Je Probe: Prüfstufe 0 (probe.Probenbau) → Läufe aller Szenarien verschränkt im Prozess-Pool (WilcoxonPruner nach
jedem Paket) → Kennzahlen, Nebenbedingungen → ab Zielwert Nachlauf und Prüfstufe 2. Ende mit genau einem Grund
(ZIEL | PLATEAU | BUDGET | FEHLER); bei Stillstand zuerst die Automatik (Bereich erweitern im Rahmen, Samplerwechsel,
Mehrfachstart), jede Maßnahme eine neue Phase (Optuna-Studie im selben Journal mit allen bisherigen Proben).
Die Bewertung (Raum, Prüfaufgabe, Simulations-Datei, Abhängigkeiten, Code) ist eingefroren (bewertung.json).
"""

import hashlib
import json
import math
import os
import queue
import random
import shutil
import time
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import optuna
import yaml
from optuna.distributions import FloatDistribution
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend, JournalFileOpenLock
from optuna.trial import TrialState, create_trial

from swki.konfig import PROJEKT
from swki.optimierung import arbeiter
from swki.optimierung.auftrag import Auftrag, abhaengigkeiten, raum
from swki.optimierung.auswertung import (Fortschritt, belastbar, erweitere, fehlerbilder, grenzanschlaege, kennzahlen,
                                         verletzung, zaehler)
from swki.optimierung.probe import Probenbau

GRUENDE = ("ZIEL", "PLATEAU", "BUDGET", "FEHLER")
STANDARD = {
    "budget": {"proben": 300, "minuten": 120, "lauf_s": 900},
    "plateau": {"proben": 20, "minuten": None, "epsilon": 0.0},
    "automatik": {"bereich_erweitern": True, "sampler": ["tpe", "qmc", "tpe_multivariat"], "mehrfachstart": 3,
                  "zufallsproben": 10},
    "pruefstufe2": {"top_k": 3, "laeufe": None, "zeitschritt_faktor": 0.5, "kontakt_faktor": 0.5, "szenarien": []},
}
ANTEIL_UNGUELTIG_MAX = 0.15
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore", category=optuna.exceptions.ExperimentalWarning)
warnings.filterwarnings("ignore", message="WilcoxonPruner finds steps")


class Ende(Exception):
    def __init__(self, grund: str, detail: str):
        super().__init__(detail)
        self.grund, self.detail = grund, detail


def _sha_dateien(pfade) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(x) for x in pfade):
        h.update(p.name.encode())
        h.update(p.read_bytes() if p.is_file() else b"<fehlt>")
    return h.hexdigest()


def code_dateien() -> list[Path]:
    return sorted((PROJEKT / "swki" / "optimierung").glob("*.py")) + sorted((PROJEKT / "swki" / "schnellbau").glob("*.py"))


def _r(x, n=6):
    return round(x, n) if isinstance(x, float) else x


class Runner:
    def __init__(self, auftrag: Auftrag, lauf: Path, kerne: int | None = None, fortsetzen: bool = False,
                 melden=None):
        self.a = auftrag
        self.lauf = lauf
        self.kerne = kerne or max(1, (os.cpu_count() or 2) - 1)
        self.melden = melden or (lambda text: None)
        blk = auftrag.block
        self.cfg = {k: {**v, **blk.get(k, {})} for k, v in STANDARD.items()}
        self.nachlauf = blk.get("nachlauf", {}).get("laeufe")
        self.neben = blk.get("nebenbedingungen", {})
        self.ungueltig_max = self.neben.get("anteil_ungueltig_max", ANTEIL_UNGUELTIG_MAX)
        self.kennzahl = auftrag.ziel["kennzahl"]
        self.anteil_ziel = "anteil_richtig" in self.kennzahl and auftrag.maximieren
        self.paket = 2 * self.kerne
        self.rahmen = {s.name: s.rahmen for s in auftrag.stellschrauben}
        self.schritt = {s.name: s.schritt for s in auftrag.stellschrauben}
        alle = [*auftrag.szenarien, *self.cfg["pruefstufe2"].get("szenarien", [])]
        self.szen_nr = {s["name"]: i for i, s in enumerate(alle)}   # fest: Saat und Schritt je Szenario
        lauf.mkdir(parents=True, exist_ok=True)
        (lauf / "proben").mkdir(exist_ok=True)
        if not fortsetzen:
            self._kopiere()
        self.specs = lauf / "specs"
        self.modul_pfad = lauf / "bewertung" / auftrag.modul.name
        sim = {}
        if auftrag.simulation is not None:
            sim = yaml.safe_load((lauf / "bewertung" / auftrag.simulation.name).read_text(encoding="utf-8")) or {}
        self.sim = sim
        self.modul = arbeiter.lade_modul(self.modul_pfad, auftrag.ordner)
        self.bewertung = self._bewertung()
        datei = lauf / "bewertung.json"
        if fortsetzen:
            alt = json.loads(datei.read_text(encoding="utf-8"))
            if alt["sha256"] != self.bewertung["sha256"]:
                raise Ende("FEHLER", "BEWERTUNG_GEAENDERT: Prüfaufgabe, Simulations-Datei, Raum oder Code weichen vom "
                                     "Stand dieses Laufs ab – nicht fortsetzbar, neuen Lauf starten")
        else:
            datei.write_text(json.dumps(self.bewertung, indent=1, ensure_ascii=False), encoding="utf-8")
        self.pb = Probenbau(auftrag, self.specs, lauf / "cache", sim)
        self.proben: list[dict] = []
        self.phasen: list[dict] = []
        self.nr = 0
        self.vorher_s = 0.0
        self.stufe2: dict[int, dict] = {}
        self.fortschritt = Fortschritt(auftrag.maximieren, self.cfg["plateau"]["epsilon"] or 0.0,
                                       self.cfg["plateau"]["proben"], self.cfg["plateau"]["minuten"])
        self._jobs_cache: dict = {}
        if fortsetzen:
            self._lies_zustand()

    # --- Lauf-Ordner ------------------------------------------------------------------------------------------------
    def _kopiere(self) -> None:
        """Feste Form und Bewertung des Laufs: alle Specs des Auftrags, Prüfaufgabe und Simulations-Datei."""
        ziel = self.lauf / "specs"
        ziel.mkdir(exist_ok=True)
        for p in self.a.ordner.glob("*.yaml"):
            shutil.copy2(p, ziel / p.name)
        b = self.lauf / "bewertung"
        b.mkdir(exist_ok=True)
        shutil.copy2(self.a.modul, b / self.a.modul.name)
        if self.a.simulation is not None:
            shutil.copy2(self.a.simulation, b / self.a.simulation.name)

    def _quellen(self) -> list[Path]:
        q = [self.a.modul, *abhaengigkeiten(self.a.block, self.a.ordner), *code_dateien()]
        return q + ([self.a.simulation] if self.a.simulation is not None else [])

    def _bewertung(self) -> dict:
        from swki.optimierung.raum import raum_summe_datei
        r = raum({"optimierung": self.a.block}, self.a.ordner)
        teile = {"raum": hashlib.sha256(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest(),
                 "dateien": _sha_dateien(self._quellen()),
                 "versionen": {"optuna": optuna.__version__, **self._versionen()}}
        return {"sha256": hashlib.sha256(json.dumps(teile, sort_keys=True).encode()).hexdigest(), **teile,
                "raum_summe": raum_summe_datei(self.a.spec_pfad), "modul": str(self.a.modul),
                "abhaengigkeiten": [str(p) for p in abhaengigkeiten(self.a.block, self.a.ordner)]}

    @staticmethod
    def _versionen() -> dict:
        out = {}
        for name in ("mujoco", "build123d"):
            try:
                out[name] = __import__(name).__version__
            except ImportError:
                out[name] = None
        return out

    def pruefe_bewertung(self) -> None:
        if _sha_dateien(self._quellen()) != self.bewertung["dateien"]:
            raise Ende("FEHLER", "BEWERTUNG_GEAENDERT: Prüfaufgabe, Simulations-Datei, Abhängigkeit oder Code wurden "
                                 "während der Studie geändert (eingefrorene Bewertung, Spec C2 §5)")

    def _zustand(self) -> None:
        z = {"nr": self.nr, "phasen": self.phasen, "zeit_s": self.zeit(),
             "stufe2": {str(k): v for k, v in self.stufe2.items()}}
        (self.lauf / "zustand.json").write_text(json.dumps(z, ensure_ascii=False), encoding="utf-8")

    def _lies_zustand(self) -> None:
        z = json.loads((self.lauf / "zustand.json").read_text(encoding="utf-8"))
        self.phasen, self.vorher_s = z["phasen"], z["zeit_s"]
        self.stufe2 = {int(k): v for k, v in z.get("stufe2", {}).items()}
        datei = self.lauf / "proben.jsonl"
        for zeile in datei.read_text(encoding="utf-8").splitlines() if datei.exists() else []:
            p = json.loads(zeile)
            self.proben.append(p)
            self.fortschritt.melde(p["nr"], self._wert_fuer_fortschritt(p), p.get("zeit_s", 0.0))
        self.nr = len(self.proben)
        if self.phasen:
            self.fortschritt.neu_beginnen(self.vorher_s)

    def zeit(self) -> float:
        return self.vorher_s + (time.perf_counter() - self._t0 if hasattr(self, "_t0") else 0.0)

    # --- Optuna -----------------------------------------------------------------------------------------------------
    def _storage(self) -> JournalStorage:
        j = str(self.lauf / "studie.journal")
        return JournalStorage(JournalFileBackend(j, lock_obj=JournalFileOpenLock(j)))

    def _sampler(self, name: str, phase: int):
        saat = 1 + phase
        if name == "qmc":
            return optuna.samplers.QMCSampler(scramble=True, seed=saat, warn_independent_sampling=False,
                                              warn_asynchronous_seeding=False)
        if name == "zufall":
            return optuna.samplers.RandomSampler(seed=saat)
        return optuna.samplers.TPESampler(seed=saat, multivariate=name == "tpe_multivariat",
                                          n_startup_trials=self.cfg["automatik"]["zufallsproben"] if phase == 0 else 0)

    def _pruner(self):
        if self.anteil_ziel:     # erst nach einem Drittel der Läufe: die Kennzahl ist ein Minimum über Szenarien
            gesamt = sum(s["laeufe"] for s in self.a.szenarien)
            return optuna.pruners.WilcoxonPruner(p_threshold=0.05, n_startup_steps=max(self.paket, gesamt // 3))
        return optuna.pruners.NopPruner()

    def verteilungen(self, phase: dict) -> dict:
        out = {}
        for name, (lo, hi) in phase["bereich"].items():
            st = self.schritt.get(name)
            if st:
                r0 = self.rahmen[name][0]
                lo = r0 + math.ceil((lo - r0) / st - 1e-9) * st
                hi = r0 + math.floor((hi - r0) / st + 1e-9) * st
            out[name] = FloatDistribution(lo, hi, step=st)
        return out

    def _studie(self, i: int, vorige=None):
        phase = self.phasen[i]
        st = optuna.create_study(study_name=f"phase-{i}", storage=self._storage(),
                                 direction="maximize" if self.a.maximieren else "minimize",
                                 sampler=self._sampler(phase["sampler"], i), pruner=self._pruner(), load_if_exists=True)
        if vorige is not None and not st.trials:
            dist = self.verteilungen(phase)
            for ft in vorige.get_trials(deepcopy=False, states=(TrialState.COMPLETE, TrialState.PRUNED)):
                st.add_trial(create_trial(state=ft.state, value=ft.value if ft.state == TrialState.COMPLETE else None,
                                          params=ft.params, distributions=dist, user_attrs=ft.user_attrs,
                                          intermediate_values=ft.intermediate_values,
                                          constraints=ft.constraints or None))
            for werte in phase.get("starts", []):
                st.enqueue_trial(werte, skip_if_exists=True)
        if i == 0 and not st.trials:
            for werte in self.a.block.get("start", []) or [self._spec_werte()]:
                st.enqueue_trial(werte)
        return st

    def _spec_werte(self) -> dict:
        """Werte der Stellschrauben in der Spec: Startpunkt, wenn der Auftrag keinen nennt."""
        out = {}
        for s in self.a.stellschrauben:
            if s.datei is not None:
                spec = yaml.safe_load((self.specs / s.datei).read_text(encoding="utf-8"))
                out[s.name] = float(spec["parameter"][s.parameter])
        return out

    # --- Läufe ------------------------------------------------------------------------------------------------------
    def _basisjobs(self, szen: dict, n: int, erster: int = 0) -> list[dict]:
        key = (szen["name"], n, erster)
        i = self.szen_nr[szen["name"]]
        if key not in self._jobs_cache:
            jobs = self.modul.jobs(szen, n, szen.get("saat", i + 1), erster)
            self._jobs_cache[key] = [dict(j, szenario=szen["name"], _schritt=i * 100000 + erster + k)
                                     for k, j in enumerate(jobs)]
        return self._jobs_cache[key]

    def jobs(self, werte: dict, szenarien: list, n_je: dict, erster: dict | None = None) -> list[dict]:
        """Läufe aller Szenarien, verschränkt (frühe Pakete decken jedes Szenario ab); Ablaufgrößen im Job."""
        ablauf = {s.ablauf: werte[s.name] for s in self.a.stellschrauben if s.ablauf and s.name in werte}
        listen = [[dict(j, **ablauf) for j in self._basisjobs(s, n_je[s["name"]], (erster or {}).get(s["name"], 0))]
                  for s in szenarien]
        out = []
        for k in range(max((len(x) for x in listen), default=0)):
            out += [x[k] for x in listen if k < len(x)]
        return out

    def rechne(self, probe_pfad: Path, jobs: list[dict], trial=None) -> tuple[dict, bool]:
        """Läufe im Pool; mit trial: in Job-Reihenfolge melden und nach jedem Paket den Pruner fragen (unabhängig davon,
        welcher Arbeitsprozess zuerst fertig ist, also wiederholbar). → ({index: Ergebnis}, abgebrochen)."""
        q: queue.Queue = queue.Queue()
        it = iter(enumerate(jobs))
        erg, offen, stop, gemeldet = {}, 0, False, 0
        pruefen = trial is not None and self.anteil_ziel

        def schicke() -> None:
            nonlocal offen
            try:
                i, job = next(it)
            except StopIteration:
                return
            self.pool.submit(arbeiter.lauf, (str(probe_pfad), job)).add_done_callback(lambda f, i=i: q.put((i, f)))
            offen += 1

        def melde(j: int) -> None:
            r = erg[j]
            if r.get("gueltig", True):
                trial.report(float(r.get("wert", r["ergebnis"] == "richtig")), step=jobs[j]["_schritt"])

        for _ in range(self.kerne + 2):
            schicke()
        while offen:
            try:
                i, f = q.get(timeout=self.cfg["budget"]["lauf_s"])
            except queue.Empty:
                raise Ende("FEHLER", f"seit {self.cfg['budget']['lauf_s']} s kein Lauf fertig (budget.lauf_s)") from None
            offen -= 1
            e = f.exception()
            if isinstance(e, BrokenProcessPool):
                raise Ende("FEHLER", f"Arbeitsprozess abgestürzt: {e}")
            if e is not None:
                raise Ende("FEHLER", f"Prüfaufgabe {self.a.modul.name} wirft in lauf(): {type(e).__name__}: {e}")
            erg[i] = f.result()
            while pruefen and not stop and gemeldet in erg:
                melde(gemeldet)
                gemeldet += 1
                if gemeldet % self.paket == 0:
                    stop = trial.should_prune()
            if not stop:
                schicke()
        if stop:                                 # nur der gemeldete Anfang zählt (wiederholbar)
            erg = {j: erg[j] for j in range(gemeldet)}
        return erg, stop

    def je_szenario(self, jobs: list[dict], erg: dict) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for i, j in enumerate(jobs):
            if i in erg:
                out.setdefault(j["szenario"], []).append(erg[i])
        return out

    def bewerte(self, laeufe: dict[str, list[dict]]) -> tuple[dict, dict]:
        """(Kennzahlen, Nebenbedingungen {Name: Verletzung})."""
        k = kennzahlen(laeufe)
        if callable(getattr(self.modul, "kennzahlen", None)):
            k.update(self.modul.kennzahlen(laeufe))
        neben = {"energie": k["anteil_ungueltig"] - self.ungueltig_max}
        for a in self.neben.get("kennzahlen", []):
            neben[a] = verletzung(a, k)
        return k, neben

    # --- Probe ------------------------------------------------------------------------------------------------------
    def _schreibe_probe(self, pfad: Path, g) -> None:
        """Probe-Datei für die Arbeitsprozesse; Prüfaufgaben mit MJCF = True bekommen das MuJoCo-Modell dazu."""
        if getattr(self.modul, "MJCF", False):
            g.daten["mjcf"] = self.pb.mjcf(g)
        pfad.write_text(json.dumps(g.daten), encoding="utf-8")

    def schlechtester(self) -> float:
        werte = [p["wert"] for p in self.proben if p.get("wert") is not None]
        if not werte:
            return 0.0
        return min(werte) if self.a.maximieren else max(werte)

    def _wert_fuer_fortschritt(self, p: dict):
        return p.get("wert") if p.get("status") == "simuliert" and p.get("zulaessig") else None

    def probe(self, trial, phase_i: int) -> dict:
        nr = self.nr
        self.nr += 1
        t0 = time.perf_counter()
        werte = dict(trial.params)
        trial.set_user_attr("nr", nr)
        g = self.pb.baue(werte)
        zeile = {"nr": nr, "phase": phase_i, "werte": {k: _r(v) for k, v in werte.items()}, "stufe0": g.stufe0(),
                 "zeiten": dict(g.zeiten)}
        if not g.gueltig:
            trial.set_constraint("befunde", float(len(g.befunde)))
            trial.set_constraint("kollision_mm3", float(sum(k["mm3"] for k in g.kollisionen)))
            trial.set_constraint("bauraum", float(len(g.bauraum)))
            self.studie.tell(trial, self.schlechtester())
            zeile.update(status="verworfen", wert=None, zulaessig=False)
        else:
            pfad = self.lauf / "proben" / f"probe_{nr:04d}.json"
            self._schreibe_probe(pfad, g)
            n_je = {s["name"]: s["laeufe"] for s in self.a.szenarien}
            jobs = self.jobs(werte, self.a.szenarien, n_je)
            t1 = time.perf_counter()
            erg, abgebrochen = self.rechne(pfad, jobs, trial)
            laeufe = self.je_szenario(jobs, erg)
            k, neben = self.bewerte(laeufe)
            wert = k.get(self.kennzahl)
            if abgebrochen:
                self.studie.tell(trial, state=TrialState.PRUNED)
                zeile.update(status="abgebrochen", wert=None, zulaessig=False, laeufe=len(erg),
                             vorlaeufig=_r(wert, 4))
            else:
                if self.nachlauf and self.a.erreicht(wert) and min(n_je.values()) < self.nachlauf:
                    erster = dict(n_je)
                    n2 = {s: max(0, self.nachlauf - n) for s, n in n_je.items()}
                    jobs2 = self.jobs(werte, [s for s in self.a.szenarien if n2[s["name"]]], n2, erster)
                    erg2, _ = self.rechne(pfad, jobs2)           # ohne Pruner: der Nachlauf wird nicht gekappt
                    for name, ls in self.je_szenario(jobs2, erg2).items():
                        laeufe.setdefault(name, []).extend(ls)
                    erg = {**erg, **{len(jobs) + i: r for i, r in erg2.items()}}
                    k, neben = self.bewerte(laeufe)
                    wert = k.get(self.kennzahl)
                if wert is None:
                    raise Ende("FEHLER", f"Kennzahl {self.kennzahl!r} fehlt (Kennzahlen: {sorted(k)[:12]})")
                for name, v in neben.items():
                    trial.set_constraint(name, float(min(v, 1e9)))
                zulaessig = all(v <= 0 for v in neben.values())
                self.studie.tell(trial, float(wert))
                zeile.update(status="simuliert", wert=_r(float(wert)), zulaessig=zulaessig, laeufe=len(erg),
                             kennzahlen={x: _r(y, 5) for x, y in k.items() if not x.startswith("gueltig:")},
                             neben={x: _r(y, 5) for x, y in neben.items() if y > 0},
                             fehlerbilder={x: round(y, 4) for x, y in list(fehlerbilder(laeufe).items())[:8]},
                             zaehler=zaehler(laeufe),
                             cpu_s_je_lauf=round(sum(r.get("_s", 0) for r in erg.values()) / max(1, len(erg)), 3))
            zeile["zeiten"]["sim_s"] = round(time.perf_counter() - t1, 2)
            pfad.unlink(missing_ok=True)
        zeile["zeiten"]["probe_s"] = round(time.perf_counter() - t0, 2)
        zeile["zeit_s"] = round(self.zeit(), 1)
        self.proben.append(zeile)
        with (self.lauf / "proben.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        self.melden(json.dumps({k: zeile.get(k) for k in ("nr", "phase", "werte", "status", "wert")},
                               ensure_ascii=False))
        return zeile

    # --- Prüfstufe 2 ------------------------------------------------------------------------------------------------
    def pruefstufe2(self, zeile: dict) -> dict:
        c = self.cfg["pruefstufe2"]
        t0 = time.perf_counter()
        gen = {"zeitschritt_faktor": c["zeitschritt_faktor"], "kontakt_faktor": c["kontakt_faktor"]}
        g = self.pb.baue(dict(zeile["werte"]), gen)
        if not g.gueltig:
            erg2 = {"bestanden": False, "abgewertet": True, "belastbar": False, "wert": None,
                    "grund": "Prüfstufe 0 nicht bestanden", "stufe0": g.stufe0()}
            self.stufe2[zeile["nr"]] = erg2
            return erg2
        pfad = self.lauf / "proben" / f"stufe2_{zeile['nr']:04d}.json"
        self._schreibe_probe(pfad, g)
        n = c["laeufe"] or 2 * max(s["laeufe"] for s in self.a.szenarien)
        szen = list(self.a.szenarien) + list(c.get("szenarien", []))
        n_je = {s["name"]: n for s in self.a.szenarien} | {s["name"]: s["laeufe"] for s in c.get("szenarien", [])}
        jobs = self.jobs(dict(zeile["werte"]), szen, n_je)
        erg, _ = self.rechne(pfad, jobs)
        pfad.unlink(missing_ok=True)
        laeufe = self.je_szenario(jobs, erg)
        k, neben = self.bewerte(laeufe)
        wert = k.get(self.kennzahl)
        normal = {s["name"] for s in self.a.szenarien}
        z2 = zaehler(laeufe)
        fest = belastbar({s: tuple(v) for s, v in zeile.get("zaehler", {}).items()},
                         {s: v for s, v in z2.items() if s in normal}) if self.anteil_ziel else True
        zulaessig = all(v <= 0 for v in neben.values())
        # abgewertet: die Probe zählt nicht mehr als Bester (nicht belastbar, Nebenbedingung, Ziel nur in Stufe 1)
        abgewertet = not fest or not zulaessig or (self.a.erreicht(zeile["wert"]) and not self.a.erreicht(wert))
        erg2 = {"bestanden": bool(self.a.erreicht(wert) and fest and zulaessig), "wert": _r(wert),
                "belastbar": fest, "zulaessig": zulaessig, "abgewertet": abgewertet, "laeufe": len(erg),
                "genauigkeit": gen,
                "kennzahlen": {x: _r(y, 5) for x, y in k.items() if not x.startswith("gueltig:")},
                "zaehler": z2, "fehlerbilder": {x: round(y, 4) for x, y in list(fehlerbilder(laeufe).items())[:8]},
                "s": round(time.perf_counter() - t0, 1)}
        self.stufe2[zeile["nr"]] = erg2
        self._zustand()
        return erg2

    # --- Rangfolge und Automatik ------------------------------------------------------------------------------------
    def rangfolge(self) -> list[dict]:
        ok = [p for p in self.proben if p.get("status") == "simuliert" and p.get("zulaessig")]
        return sorted(ok, key=lambda p: (-p["wert"] if self.a.maximieren else p["wert"], -p.get("laeufe", 0), p["nr"]))

    def bester(self) -> dict | None:
        r = [p for p in self.rangfolge() if not self.stufe2.get(p["nr"], {}).get("abgewertet", False)]
        return r[0] if r else None

    def gleich_gute(self, best: dict, n: int = 3) -> list[dict]:
        """Die Besten, die vom Besten höchstens epsilon abweichen (höchstens n)."""
        eps = self.cfg["plateau"]["epsilon"] or 0.0
        return [p for p in self.rangfolge() if abs(p["wert"] - best["wert"]) <= eps + 1e-12
                and not self.stufe2.get(p["nr"], {}).get("abgewertet", False)][:n] or [best]

    def automatik(self, phase: dict) -> dict | None:
        cfg = self.cfg["automatik"]
        best = self.bester()
        if best is None:
            return None
        bereich = {k: tuple(v) for k, v in phase["bereich"].items()}
        if cfg["bereich_erweitern"]:
            an, gesehen = [], set()
            for p in self.gleich_gute(best):     # unter gleich guten Proben zählt jede an der Grenze
                for x in grenzanschlaege(p["werte"], bereich, self.rahmen):
                    if x["erweiterbar"] and (x["name"], x["seite"]) not in gesehen:
                        gesehen.add((x["name"], x["seite"]))
                        an.append(x)
            if an:
                neu = dict(bereich)
                for x in an:
                    neu[x["name"]] = erweitere(neu[x["name"]], self.rahmen[x["name"]], x["seite"])
                return {"massnahme": "bereich_erweitert", "sampler": phase["sampler"], "sampler_i": phase["sampler_i"],
                        "bereich": {k: list(v) for k, v in neu.items()},
                        "detail": ", ".join(f"{x['name']} {x['seite']} → {neu[x['name']]}" for x in an)}
        if phase["sampler_i"] + 1 < len(cfg["sampler"]):
            i = phase["sampler_i"] + 1
            rng = random.Random(len(self.phasen))
            starts = []
            for p in self.rangfolge()[:cfg["mehrfachstart"]]:      # Mehrfachstart: die Besten leicht versetzt
                w = {}
                for name, v in p["werte"].items():
                    lo, hi = bereich[name]
                    x = min(hi, max(lo, v + rng.gauss(0, 0.05 * (hi - lo))))
                    st = self.schritt.get(name)
                    if st:
                        r0 = self.rahmen[name][0]
                        x = min(hi, max(lo, r0 + round((x - r0) / st) * st))
                    w[name] = x
                starts.append(w)
            return {"massnahme": "samplerwechsel", "sampler": cfg["sampler"][i], "sampler_i": i,
                    "bereich": {k: list(v) for k, v in bereich.items()}, "starts": starts,
                    "detail": f"{phase['sampler']} → {cfg['sampler'][i]}, {len(starts)} Neustarts"}
        return None

    # --- Hauptschleife ----------------------------------------------------------------------------------------------
    def _schleife(self) -> tuple[str, str]:
        b = self.cfg["budget"]
        if not self.phasen:
            self.phasen.append({"nr_ab": 0, "massnahme": "start", "sampler": self.cfg["automatik"]["sampler"][0],
                                "sampler_i": 0, "bereich": {s.name: list(s.bereich) for s in self.a.stellschrauben}})
        i = len(self.phasen) - 1
        self.studie = self._studie(i)
        while True:
            self.pruefe_bewertung()
            if (self.lauf / "stop").exists():
                return "BUDGET", "angehalten (Datei stop im Lauf-Ordner)"
            if self.nr >= b["proben"]:
                return "BUDGET", f"{b['proben']} Proben erreicht"
            if b.get("minuten") and self.zeit() >= 60 * b["minuten"]:
                return "BUDGET", f"{b['minuten']} min erreicht"
            trial = self.studie.ask(self.verteilungen(self.phasen[i]))
            zeile = self.probe(trial, i)
            self.fortschritt.melde(zeile["nr"], self._wert_fuer_fortschritt(zeile), self.zeit())
            if zeile["status"] == "verworfen" and zeile["nr"] == 0 and zeile["stufe0"]["befunde"]:
                return "FEHLER", f"Startprobe nicht baubar: {zeile['stufe0']['befunde'][0]}"
            if self._wert_fuer_fortschritt(zeile) is not None and self.a.erreicht(zeile["wert"]):
                s2 = self.pruefstufe2(zeile)
                self.melden(f"Prüfstufe 2 Probe {zeile['nr']}: {json.dumps(s2['bestanden'])} ({s2['wert']})")
                if s2["bestanden"]:
                    return "ZIEL", (f"Probe {zeile['nr']} erreicht {self.kennzahl} {zeile['wert']:g} "
                                    f"(Ziel {self.a.ziel['zielwert']:g}) und besteht Prüfstufe 2 ({s2['wert']:g})")
                rest = self.bester()                  # abgewertet: Vergleichswert zurück auf den besten verbliebenen
                self.fortschritt.bester = None if rest is None else (rest["nr"], rest["wert"])
            self._zustand()
            if self.fortschritt.stillstand(zeile["nr"], self.zeit()):
                m = self.automatik(self.phasen[i])
                p = self.cfg["plateau"]
                warum = (f"{p['proben']} Proben" if p["proben"] else "") + \
                        (f" / {p['minuten']} min" if p.get("minuten") else "") + \
                        f" ohne Verbesserung > {p['epsilon']:g}"
                if m is None:
                    return "PLATEAU", f"{warum}; Automatik erschöpft ({len(self.phasen)} Phasen)"
                m["nr_ab"] = self.nr
                self.phasen.append(m)
                self.melden(f"Automatik: {m['massnahme']} ({m['detail']})")
                vorige = self.studie
                i += 1
                self.studie = self._studie(i, vorige)
                self.fortschritt.neu_beginnen(self.zeit())
                self._zustand()

    def starte(self) -> dict:
        from swki.optimierung import bericht
        self._t0 = time.perf_counter()
        grund, detail = "FEHLER", ""
        try:
            with ProcessPoolExecutor(self.kerne, initializer=arbeiter.init,
                                     initargs=(str(self.modul_pfad), str(self.a.ordner))) as pool:
                self.pool = pool
                try:
                    grund, detail = self._schleife()
                except Ende as e:
                    grund, detail = e.grund, e.detail
                if grund in ("PLATEAU", "BUDGET"):
                    for p in [p for p in self.rangfolge() if p["nr"] not in self.stufe2][:self.cfg["pruefstufe2"]["top_k"]]:
                        self.pruefstufe2(p)
        except Ende as e:
            grund, detail = e.grund, e.detail
        except KeyboardInterrupt:
            grund, detail = "FEHLER", "abgebrochen (KeyboardInterrupt)"
        except Exception as e:
            grund, detail = "FEHLER", f"{type(e).__name__}: {e} | {traceback.format_exc(limit=3)[-600:]}"
        self._zustand()
        status = bericht.status(self, grund, detail)
        bericht.schreibe(status, self.lauf)
        return status
