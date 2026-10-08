"""Kommandozeile des Messstands (Ausgabe JSON).

  referenz <aufgabe>                         Referenz-STL einmalig erzeugen (MESSSTAND/referenz/<aufgabe>.stl)
  vorbereiten <durchgang> <aufgabe> <nr>     Worktree + Auftrag anlegen, SolidWorks neu starten, Abtaster starten;
                                             gibt den Prompt für den Konstruktions-Agenten aus
  abschliessen <lauf> --agent <id>           Abtaster stoppen, Transkripte/Protokolle auswerten, STL vergleichen → kpi.json
  score <durchgang> [--baseline 0]           Score des Durchgangs → score.json
  aufraeumen <durchgang>                     Worktrees des Durchgangs entfernen
  abtasten <datei> <stopp>                   (intern) Speicher-Abtaster
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from swki.konfig import lade_rechner
from werkzeuge.messstand import abtaster, protokolle, score, transkript
from werkzeuge.messstand.umgebung import (REPO, auftrag_anlegen, auftrag_name, aufgaben, lauf_id, lauf_ordner,
                                          lies_json, messordner, prompt, schreibe_json, worktree_anlegen,
                                          worktree_entfernen)


def _swki(*args, cwd=REPO) -> dict:
    p = subprocess.run([sys.executable, "-m", "swki", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8")
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        d = {"stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    d["_exit"] = p.returncode
    return d


def referenz(args) -> dict:
    a = aufgaben()[args.aufgabe]
    r = lade_rechner()
    ziel = messordner() / "referenz" / f"{a.id}.stl"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    from werkzeuge.messstand.stl_export import exportiere
    if "datei" in a.referenz:
        quelle = Path(a.referenz["datei"].format(arbeitsordner=r.arbeitsordner))
        return {"aufgabe": a.id, "quelle": str(quelle), "stl": str(exportiere(quelle, ziel))}
    auftrag = REPO / "auftraege" / f"MESSREF-{a.id}"
    if auftrag.exists():
        shutil.rmtree(auftrag)
    shutil.copytree(REPO / a.referenz["spec_ordner"], auftrag,
                    ignore=shutil.ignore_patterns("__pycache__", "*.py", "protokolle", "*.freigegeben.yaml",
                                                  "freigabe.json"))
    for unter in ("skripte",):   # Skripte gehören zum Bauweg
        q = REPO / a.referenz["spec_ordner"] / unter
        if q.is_dir():
            shutil.copytree(q, auftrag / unter, dirs_exist_ok=True)
    spec = auftrag / a.referenz["spec"]
    fr = _swki("freigeben", str(spec))
    if fr["_exit"]:
        return {"aufgabe": a.id, "status": "fehler", "freigeben": fr}
    bau = _swki("bauen", str(spec))
    if bau["_exit"]:
        return {"aufgabe": a.id, "status": "fehler", "bauen": bau}
    lauf = bau.get("lauf")
    datei = protokolle.ergebnisdatei(r.arbeitsordner / auftrag.name / f"lauf-{lauf}")
    return {"aufgabe": a.id, "lauf": lauf, "quelle": str(datei), "stl": str(exportiere(datei, ziel))}


def vorbereiten(args) -> dict:
    alle = aufgaben()
    a = alle[args.aufgabe]
    lauf = lauf_id(args.durchgang, a.id, args.nr)
    lo = lauf_ordner(lauf)
    if lo.exists():
        shutil.rmtree(lo)
    lo.mkdir(parents=True)
    commit = subprocess.run(["git", "rev-parse", args.commit], cwd=REPO, capture_output=True, text=True,
                            check=True).stdout.strip()
    wt = worktree_anlegen(lauf, commit, alle)
    auftrag = auftrag_anlegen(wt, lauf, a)
    alt = lade_rechner().arbeitsordner / auftrag_name(lauf)
    if alt.exists():
        shutil.rmtree(alt)
    from werkzeuge.sw_neustart import neustart
    neu = neustart()
    pid = abtaster.starte(lo / "speicher.jsonl", lo / "abtaster.stopp")
    text = prompt(lauf, wt, a)
    (lo / "prompt.md").write_text(text, encoding="utf-8")
    info = {"lauf": lauf, "durchgang": args.durchgang, "aufgabe": a.id, "nr": args.nr, "commit": commit,
            "wt": str(wt), "auftrag": str(auftrag), "abtaster_pid": pid, "neustart": neu,
            "vorbereitet": datetime.now().isoformat(timespec="seconds")}
    schreibe_json(lo / "lauf.json", info)
    return {**info, "prompt": text}


def _verboten(a) -> list[str]:
    r = lade_rechner()
    return [str(REPO / "auftraege"), str(r.arbeitsordner / "AP68-Pruefstation"), str(messordner() / "referenz"),
            *(str(REPO / v) for v in a.verboten)]


def abschliessen(args) -> dict:
    lo = lauf_ordner(args.lauf)
    info = lies_json(lo / "lauf.json")
    a = aufgaben()[info["aufgabe"]]
    r = lade_rechner()
    abtaster.stoppe(lo / "abtaster.stopp", lo / "speicher.jsonl")
    sp = abtaster.auswerten(lo / "speicher.jsonl")

    pfad = transkript.finde_transkript(args.agent)
    ziel = lo / "transkripte"
    ziel.mkdir(exist_ok=True)
    shutil.copy2(pfad, ziel / pfad.name)
    unter = {}
    for kid, p in transkript.subagenten(pfad.parent, args.agent).items():
        if p.exists():
            shutil.copy2(p, ziel / p.name)
            unter[kid] = transkript.lade(p)
    tk = transkript.auswerten(transkript.lade(pfad), unter, _verboten(a))

    auftrag = Path(info["auftrag"])
    pk = protokolle.auswerten(auftrag)
    erg = {"richtig": False, "vergleich": None, "ergebnisdatei": None}
    if pk["letzter_lauf"]:
        datei = protokolle.ergebnisdatei(r.arbeitsordner / auftrag.name / f"lauf-{pk['letzter_lauf']}")
        ref = messordner() / "referenz" / f"{a.id}.stl"
        if datei and ref.exists():
            from werkzeuge.messstand.stl_export import exportiere
            from werkzeuge.messstand.vergleich import vergleiche
            stl = exportiere(datei, lo / "ergebnis.stl")
            v = vergleiche(stl, ref)
            erg = {"richtig": v["richtig"], "gespiegelt": v["gespiegelt"], "vergleich": v["beste"],
                   "ergebnisdatei": str(datei)}
    kpi = {"lauf": args.lauf, "durchgang": info["durchgang"], "aufgabe": a.id, "commit": info["commit"],
           **tk, **pk, **sp, "bestanden": pk["pruefer_bestanden"], **erg,
           "haenger": args.haenger, "abgeschlossen": datetime.now().isoformat(timespec="seconds")}
    schreibe_json(lo / "kpi.json", kpi)
    kurz = {k: kpi[k] for k in ("lauf", "zeit_s", "zeit_anteile_s", "tool_aufrufe", "laeufe", "bauabbrueche",
                                 "pruefmaengel", "pruefer_maengel", "freigaben", "speicher_spitze_mb",
                                 "sw_neustarts", "bestanden", "richtig", "lecks")}
    kurz["tokens_gewichtet"] = kpi["tokens"]["gewichtet"]
    return kurz


def _kpis(durchgang: int) -> list[dict]:
    return [lies_json(p) for p in sorted((messordner() / f"durchgang-{durchgang}").glob("*/kpi.json"))]


def score_befehl(args) -> dict:
    b = score.bezug(_kpis(args.baseline))
    erg = score.bewerte(_kpis(args.durchgang), b)
    if args.durchgang == args.baseline:
        erg = {**erg, "score_selbst": erg["score"], "score": 2.0, "hinweis": "Baseline: Score-Anker 2,0 (Nutzer)"}
    erg["bezug"] = b
    schreibe_json(messordner() / f"durchgang-{args.durchgang}" / "score.json", erg)
    return erg


def aufraeumen(args) -> dict:
    weg = []
    for wt in sorted((messordner() / "wt").glob(f"d{args.durchgang}-*")):
        worktree_entfernen(wt)
        weg.append(wt.name)
    return {"entfernt": weg}


def main() -> int:
    p = argparse.ArgumentParser(prog="messstand", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("referenz"); s.add_argument("aufgabe"); s.set_defaults(f=referenz)
    s = sub.add_parser("vorbereiten"); s.add_argument("durchgang", type=int); s.add_argument("aufgabe")
    s.add_argument("nr", type=int); s.add_argument("--commit", default="HEAD"); s.set_defaults(f=vorbereiten)
    s = sub.add_parser("abschliessen"); s.add_argument("lauf"); s.add_argument("--agent", required=True)
    s.add_argument("--haenger", type=int, default=0); s.set_defaults(f=abschliessen)
    s = sub.add_parser("score"); s.add_argument("durchgang", type=int); s.add_argument("--baseline", type=int, default=0)
    s.set_defaults(f=score_befehl)
    s = sub.add_parser("aufraeumen"); s.add_argument("durchgang", type=int); s.set_defaults(f=aufraeumen)
    s = sub.add_parser("abtasten"); s.add_argument("datei", type=Path); s.add_argument("stopp", type=Path)
    s.set_defaults(f=None)
    args = p.parse_args()
    if args.befehl == "abtasten":
        abtaster.abtasten(args.datei, args.stopp)
        return 0
    beginn = time.time()
    erg = args.f(args)
    erg["dauer_s"] = round(time.time() - beginn, 1)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(erg, ensure_ascii=False, indent=2, default=str))
    return 0 if erg.get("status") != "fehler" else 1


if __name__ == "__main__":
    sys.exit(main())
