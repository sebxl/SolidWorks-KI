"""Kommandozeile des Messstands (Ausgabe JSON).

  referenz <aufgabe>                         Referenz-STL einmalig erzeugen (MESSSTAND/referenz/<aufgabe>.stl)
  vorbereiten <durchgang> <aufgabe> <nr>     Worktree + Auftrag anlegen, SolidWorks neu starten, Abtaster starten;
                                             gibt den Prompt für den Konstruktions-Agenten aus
  abschliessen <lauf> --agent <id>           Abtaster stoppen, Transkripte/Protokolle auswerten, STL vergleichen → kpi.json
  score <durchgang> [--baseline 0]           Score des Durchgangs → score.json (Messstand 09.10.)
  btp <durchgang> [--vergleich n]            Score nach dem Bewertungsbogen (Spec 2026-10-23) → btp.json
  btp-mittel <n> <m> [--vergleich k l]       Score aus dem Mittel der Durchgänge (§5.1 ab Umbau 2) → btp-mittel-<n>-<m>.json
  vorlage <aufgabe> <quelle> [--referenz]    Auftrag als Vorlage (bzw. Referenz-Specs) der Änderungsaufgabe einfrieren
  fallen bauen [<id> …]                      Präzisions-Fallen bauen und prüfen (MESSSTAND/fallen/<id>/stand.json)
  fallen auftraege <durchgang>               Prüf-Prompts je Falle (×3) → durchgang-<n>/fallen/auftraege.json
  fallen auswerten <durchgang>               Urteile auswerten → durchgang-<n>/fallen/fallen.json
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
from werkzeuge.messstand import abtaster, btp, fallen, protokolle, score, transkript
from werkzeuge.messstand.umgebung import (QUELLREPO, REPO, auftrag_anlegen, auftrag_name, aufgaben, lauf_id,
                                          lauf_ordner, lies_json, messordner, prompt, schreibe_json,
                                          vorlage_kopieren, worktree_anlegen, worktree_entfernen)


def _neustart() -> dict:
    from werkzeuge.sw_neustart import neustart
    return neustart()


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
    quelle = Path(a.referenz["spec_ordner"].format(arbeitsordner=r.arbeitsordner))
    quelle = quelle if quelle.is_absolute() else REPO / quelle
    shutil.copytree(quelle, auftrag,
                    ignore=shutil.ignore_patterns("__pycache__", "*.py", "protokolle", "*.freigegeben.yaml",
                                                  "freigabe.json"))
    for unter in ("skripte",):   # Skripte gehören zum Bauweg
        q = quelle / unter
        if q.is_dir():
            shutil.copytree(q, auftrag / unter, dirs_exist_ok=True)
    spec = auftrag / a.referenz["spec"]
    fr = _swki("freigeben", str(spec))
    if fr["_exit"]:
        return {"aufgabe": a.id, "status": "fehler", "freigeben": fr}
    if a.art == "baugruppe":
        _neustart()
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
    ausgang = _ausgangslauf(wt, auftrag, a) if a.ausgangslauf else None
    if ausgang and ausgang.get("status") == "fehler":
        return {"lauf": lauf, "status": "fehler", "ausgangslauf": ausgang}
    neu = _neustart()
    pid = abtaster.starte(lo / "speicher.jsonl", lo / "abtaster.stopp")
    text = prompt(lauf, wt, a)
    (lo / "prompt.md").write_text(text, encoding="utf-8")
    info = {"lauf": lauf, "durchgang": args.durchgang, "aufgabe": a.id, "nr": args.nr, "commit": commit,
            "wt": str(wt), "auftrag": str(auftrag), "abtaster_pid": pid, "neustart": neu,
            "ausgangslauf": ausgang["lauf"] if ausgang else None,
            "vorbereitet": datetime.now().isoformat(timespec="seconds")}
    schreibe_json(lo / "lauf.json", info)
    return {**info, "prompt": text}


def _ausgangslauf(wt: Path, auftrag: Path, a) -> dict:
    """Vorlage mit dem gemessenen Stand bauen und prüfen (Code des Worktrees), Prüfer-Urteil wie im Betrieb bestanden.
    Liegt außerhalb von zeit_s (Bogen §2.1)."""
    spec = auftrag / a.spec
    beginn = time.time()
    _neustart()
    bau = _swki("bauen", str(spec), cwd=wt)
    if bau["_exit"] or bau.get("status") != "ok":
        return {"status": "fehler", "schritt": "bauen", "bauen": bau}
    _neustart()
    pr = _swki("pruefen", str(spec), "--lauf", str(bau["lauf"]), cwd=wt)
    if pr["_exit"] or not pr.get("bestanden"):
        return {"status": "fehler", "schritt": "pruefen", "lauf": bau["lauf"],
                "pruefen": {k: pr.get(k) for k in ("bestanden", "maengel", "stdout", "stderr")}}
    urteil = auftrag / "protokolle" / f"{spec.stem}.lauf-{bau['lauf']}.pruefer.json"
    urteil.write_text(json.dumps({"bestanden": True, "maengel": [], "hinweis": "Ausgangslauf des Messstands"},
                                 ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "lauf": bau["lauf"], "dauer_s": round(time.time() - beginn, 1)}


def _verboten(a) -> list[str]:
    r = lade_rechner()
    return [str(QUELLREPO), str(REPO), str(r.arbeitsordner / "AP68-Pruefstation"), str(messordner() / "referenz"),
            str(messordner() / "vorlagen"), str(messordner() / "fallen"),
            *(str(QUELLREPO / v) for v in a.verboten)]


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
    ab = info.get("ausgangslauf")
    pk = protokolle.auswerten(auftrag, ab_lauf=ab + 1 if ab else None)
    erg = {"richtig": False, "vergleich": None, "ergebnisdatei": None}
    if pk["letzter_lauf"]:
        datei = protokolle.ergebnisdatei(r.arbeitsordner / auftrag.name / f"lauf-{pk['letzter_lauf']}")
        ref = messordner() / "referenz" / f"{a.id}.stl"
        if datei and ref.exists():
            stl = lo / "ergebnis.stl"
            if not stl.exists():
                from werkzeuge.messstand.stl_export import exportiere
                exportiere(datei, stl)
            erg = {"richtig": None, "vergleich": None, "ergebnisdatei": str(datei)}
            if not args.ohne_vergleich:
                from werkzeuge.messstand.vergleich import vergleiche
                v = vergleiche(stl, ref)
                erg |= {"richtig": v["richtig"], "gespiegelt": v["gespiegelt"], "vergleich": v["beste"]}
    kpi = {"lauf": args.lauf, "durchgang": info["durchgang"], "aufgabe": a.id, "commit": info["commit"],
           **tk, **pk, **sp, "bestanden": pk["pruefer_bestanden"], **erg,
           "haenger": args.haenger, "abgeschlossen": datetime.now().isoformat(timespec="seconds")}
    if args.wiederholung_von:
        kpi |= {"wiederholung_von": args.wiederholung_von, "original_fehler_zaehlen": args.original_fehler_zaehlen}
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


def btp_befehl(args) -> dict:
    """Score nach dem Bewertungsbogen; Bezug = Durchgang 0, Vergleich (optional) = aktueller Stand."""
    b = btp.bezug(_kpis(0))

    erg = _btp_bewertet(args.durchgang, b)
    if args.vergleich is not None:
        alt, d0 = _btp_bewertet(args.vergleich, b), _btp_bewertet(0, b)
        ok, grund = btp.besser(erg, alt, d0)
        erg["entscheidung"] = {"gegen": args.vergleich, "besser": ok, "grund": grund, "score_vorher": alt["score"]}
    erg["bezug"] = b
    schreibe_json(messordner() / f"durchgang-{args.durchgang}" / "btp.json", erg)
    return erg


def _fallen_von(n: int) -> dict:
    f = _fallen_ordner(n) / "fallen.json"
    if not f.exists():
        raise SystemExit(f"{f} fehlt – zuerst: fallen auswerten {n}")
    return lies_json(f)


def _btp_bewertet(n: int, b: dict) -> dict:
    return btp.bewerte(_kpis(n), _fallen_von(n), b)


def btp_mittel_befehl(args) -> dict:
    """Score aus dem Mittel mehrerer Durchgänge (Bogen §5.1 ab Umbau 2), Entscheidung gegen das Mittel des Stands."""
    b = btp.bezug(_kpis(0))
    erg = btp.mittel([(_kpis(n), _fallen_von(n)) for n in args.durchgaenge], b)
    name = "-".join(map(str, args.durchgaenge))
    if args.vergleich:
        alt = btp.mittel([(_kpis(n), _fallen_von(n)) for n in args.vergleich], b)
        ok, grund = btp.besser(erg, alt, _btp_bewertet(0, b))
        erg["entscheidung"] = {"gegen": args.vergleich, "besser": ok, "grund": grund, "score_vorher": alt["score"],
                               "teilscores_vorher": alt["teilscores"], "werte_vorher": alt["werte"]}
    erg["einzeln"] = {n: _btp_bewertet(n, b)["score"] for n in args.durchgaenge}
    schreibe_json(messordner() / f"btp-mittel-{name}.json", erg)
    return erg


def vorlage(args) -> dict:
    a = aufgaben()[args.aufgabe]
    r = lade_rechner()
    if args.referenz:
        ziel = Path(a.referenz["spec_ordner"].format(arbeitsordner=r.arbeitsordner))
    else:
        ziel = a.vorlage_pfad(r.arbeitsordner)
    vorlage_kopieren(Path(args.quelle), ziel)
    return {"aufgabe": a.id, "ziel": str(ziel),
            "dateien": sorted(str(p.relative_to(ziel)) for p in ziel.rglob("*") if p.is_file())}


def _fallen_ordner(durchgang: int) -> Path:
    return messordner() / f"durchgang-{durchgang}" / "fallen"


def _commit(ref: str = "HEAD") -> str:
    return subprocess.run(["git", "rev-parse", ref], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def fallen_bauen(args) -> dict:
    alle = fallen.fallen()
    erg = {}
    for fid in args.ids or sorted(alle):
        f = alle[fid]
        auftrag = fallen.auftrag_anlegen(f, REPO / "auftraege", lade_rechner().arbeitsordner)
        spec = auftrag / f.spec
        alt = lade_rechner().arbeitsordner / f.auftrag
        if alt.exists():
            shutil.rmtree(alt)
        schritte = {"freigeben": _swki("freigeben", str(spec))}
        if not schritte["freigeben"]["_exit"]:
            _neustart()
            schritte["bauen"] = _swki("bauen", str(spec))
        if "bauen" in schritte and not schritte["bauen"]["_exit"]:
            _neustart()
            schritte["pruefen"] = _swki("pruefen", str(spec))
        pr = schritte.get("pruefen") or {}
        stand = {"id": fid, "art": f.art, "spec": str(spec), "lauf": (schritte.get("bauen") or {}).get("lauf"),
                 "gebaut": "pruefen" in schritte and not pr.get("_exit"), "swki_bestanden": pr.get("bestanden"),
                 "commit": _commit(),
                 "fehler": {k: {x: v.get(x) for x in ("fehler", "stdout", "stderr", "_exit")}
                            for k, v in schritte.items() if v.get("_exit")}}
        schreibe_json(messordner() / "fallen" / fid / "stand.json", stand)
        erg[fid] = {k: stand[k] for k in ("lauf", "gebaut", "swki_bestanden", "fehler")}
    return {"fallen": erg, "status": "ok" if all(v["gebaut"] for v in erg.values()) else "fehler"}


def fallen_auftraege(args) -> dict:
    from swki.durchlauf import pruefer_auftrag
    pruefer_md = subprocess.run(["git", "show", f"{args.commit}:.claude/agents/pruefer.md"], cwd=REPO,
                                capture_output=True, text=True, encoding="utf-8", check=True).stdout
    ordner = _fallen_ordner(args.durchgang)
    ordner.mkdir(parents=True, exist_ok=True)
    auftraege, swki_treffer = [], []
    for fid in sorted(fallen.fallen()):
        stand = lies_json(messordner() / "fallen" / fid / "stand.json")
        if not stand["gebaut"]:
            raise SystemExit(f"Falle {fid} ist nicht gebaut – zuerst: fallen bauen {fid}")
        if stand["swki_bestanden"] is False:
            swki_treffer.append(fid)
            continue
        spec = Path(stand["spec"])
        bericht = lies_json(spec.parent / "protokolle" / f"{spec.stem}.lauf-{stand['lauf']}.pruefbericht.json")
        text = fallen.pruefauftrag(pruefer_md, pruefer_auftrag(spec, stand["lauf"], bericht))
        for k in range(1, fallen.WIEDERHOLUNGEN + 1):
            datei = ordner / f"auftrag-{fid}-{k}.md"   # damit der Orchestrator den Prompt nicht abschreiben muss
            datei.write_text(text, encoding="utf-8")
            auftraege.append({"id": fid, "k": k, "urteil": str(ordner / f"urteil-{fid}-{k}.json"), "prompt": text,
                              "datei": str(datei)})
    (ordner / "swki_treffer.json").write_text(json.dumps(swki_treffer), encoding="utf-8")
    schreibe_json(ordner / "auftraege.json", {"commit": _commit(args.commit), "auftraege": auftraege})
    return {"auftraege": len(auftraege), "swki_treffer": swki_treffer, "datei": str(ordner / "auftraege.json"),
            "hinweis": "Je Auftrag einen unabhängigen Agenten (nur Read/Glob) mit dem Prompt starten und nur dessen "
                       "JSON-Urteil unverändert in die Datei 'urteil' schreiben; danach: fallen auswerten"}


def fallen_auswerten(args) -> dict:
    erg = fallen.auswerten(_fallen_ordner(args.durchgang))
    schreibe_json(_fallen_ordner(args.durchgang) / "fallen.json", erg)
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
    s.add_argument("--haenger", type=int, default=0)
    s.add_argument("--ohne-vergleich", action="store_true", help="nur exportieren, Vergleich später")
    s.add_argument("--wiederholung-von", help="Lauf, den dieser Lauf wiederholt (Bogen §5.1)")
    s.add_argument("--original-fehler-zaehlen", action="store_true",
                   help="Fehlerpunkte des wiederholten Laufs zählen mit (Durchgang 0)")
    s.set_defaults(f=abschliessen)
    s = sub.add_parser("score"); s.add_argument("durchgang", type=int); s.add_argument("--baseline", type=int, default=0)
    s.set_defaults(f=score_befehl)
    s = sub.add_parser("btp"); s.add_argument("durchgang", type=int); s.add_argument("--vergleich", type=int)
    s.set_defaults(f=btp_befehl)
    s = sub.add_parser("btp-mittel"); s.add_argument("durchgaenge", type=int, nargs="+")
    s.add_argument("--vergleich", type=int, nargs="+"); s.set_defaults(f=btp_mittel_befehl)
    s = sub.add_parser("vorlage"); s.add_argument("aufgabe"); s.add_argument("quelle")
    s.add_argument("--referenz", action="store_true"); s.set_defaults(f=vorlage)
    s = sub.add_parser("fallen"); fs = s.add_subparsers(dest="fallen_befehl", required=True)
    x = fs.add_parser("bauen"); x.add_argument("ids", nargs="*"); x.set_defaults(f=fallen_bauen)
    x = fs.add_parser("auftraege"); x.add_argument("durchgang", type=int); x.add_argument("--commit", default="HEAD")
    x.set_defaults(f=fallen_auftraege)
    x = fs.add_parser("auswerten"); x.add_argument("durchgang", type=int); x.set_defaults(f=fallen_auswerten)
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
