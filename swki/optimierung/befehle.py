"""Befehl "swki optimiere <spec>" (Spec C2 §4) und "swki optimiere <spec> --uebernehmen" (§6).

Ohne SolidWorks; braucht das Extra `schnellbau`. Fortschritt je Probe auf stderr und in <lauf>/fortschritt.log, am Ende
JSON wie alle swki-Befehle (Kurzfassung; vollständig in <lauf>/status.json, für Claude <lauf>/plateau.md).
"""

import json
import math
import re
import sys
from pathlib import Path

import yaml

from swki.auftrag import auftrag_name, auftrag_ordner
from swki.cli import SwkiFehler
from swki.konfig import lade_rechner
from swki.spec.laden import art_der_datei, lade_spec

_LAUF = re.compile(r"^optimierung-(\d+)$")


def _laden(pfad: Path) -> dict:
    """Spec mit Block laden und vollständig prüfen (Baugruppe samt Teil-Specs)."""
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.laden import lade_baugruppe
        spec = lade_baugruppe(pfad).spec
    else:
        spec = lade_spec(pfad)
    if "optimierung" not in spec:
        raise SwkiFehler(f"{pfad.name} hat keinen Block optimierung (Spec C2 §2)")
    return spec


def laeufe(ordner: Path) -> list[int]:
    if not ordner.is_dir():
        return []
    return sorted(int(m.group(1)) for p in ordner.iterdir() if p.is_dir() and (m := _LAUF.match(p.name)))


def _ordner(args, pfad: Path) -> Path:
    if args.arbeitsordner:
        return Path(args.arbeitsordner) / auftrag_name(pfad)
    return auftrag_ordner(lade_rechner(), auftrag_name(pfad))


def _optimiere(args) -> dict:
    pfad = Path(args.spec).resolve()
    if args.uebernehmen:
        return uebernehmen(pfad, _ordner(args, pfad), args.lauf, args.probe)
    try:
        from swki.optimierung.auftrag import lies_auftrag
        from swki.optimierung.runner import Ende, Runner
    except ImportError as e:
        raise SwkiFehler(f"Extra 'schnellbau' fehlt ({e.name}): pip install -e .[schnellbau]") from e
    spec = _laden(pfad)
    basis = _ordner(args, pfad)
    if args.fortsetzen:
        lauf = basis / f"optimierung-{args.fortsetzen}"
        if not (lauf / "zustand.json").is_file():
            raise SwkiFehler(f"{lauf} ist kein fortsetzbarer Lauf (zustand.json fehlt)")
    else:
        lauf = basis / f"optimierung-{max(laeufe(basis), default=0) + 1}"
    lauf.mkdir(parents=True, exist_ok=True)
    log = (lauf / "fortschritt.log").open("a", encoding="utf-8")

    def melden(text: str) -> None:
        print(text, file=sys.stderr, flush=True)
        log.write(text + "\n")
        log.flush()

    try:
        r = Runner(lies_auftrag(spec, pfad), lauf, kerne=args.kerne, fortsetzen=bool(args.fortsetzen), melden=melden)
        s = r.starte()
    except Ende as e:
        raise SwkiFehler(f"{e.grund}: {e.detail}") from e
    finally:
        log.close()
    b = s.get("bester") or {}
    return {"grund": s["grund"], "detail": s["detail"], "lauf": str(lauf), "plateau_md": str(lauf / "plateau.md"),
            "status_json": str(lauf / "status.json"), "raum_freigegeben": s["raum_freigegeben"],
            "proben": s["proben"], "bester": {k: b.get(k) for k in ("nr", "wert", "werte", "stufe2")} if b else None,
            "naechster_schritt": s["naechster_schritt"]}


# --- Übernehmen -------------------------------------------------------------------------------------------------------
def _zahl(wert: float, schritt: float | None, lo: float) -> float:
    if schritt:
        wert = lo + round((wert - lo) / schritt) * schritt
        stellen = max(0, -math.floor(math.log10(schritt)) + 2)
        return round(wert, stellen)
    return round(wert, 4)


def _text(wert: float) -> str:
    return f"{wert:.6f}".rstrip("0").rstrip(".") if wert != int(wert) else str(int(wert))


def setze_parameter(pfad: Path, name: str, wert: float) -> None:
    """Wert eines Parameters im YAML-Text ersetzen (Kommentare bleiben); Block- oder Fluss-Schreibweise."""
    text = pfad.read_text(encoding="utf-8")
    zeilen = text.splitlines(keepends=True)
    neu, in_block, getroffen = [], False, False
    zahl = r"-?[0-9][0-9_.eE+-]*"
    for z in zeilen:
        if re.match(r"^parameter:\s*\{", z):
            z2 = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(name)}(\s*:\s*){zahl}", lambda m: f"{name}{m.group(1)}{_text(wert)}",
                        z, count=1)
            getroffen = getroffen or z2 != z
            neu.append(z2)
            continue
        if re.match(r"^parameter:\s*(#.*)?$", z):
            in_block = True
        elif in_block and re.match(r"^\S", z):
            in_block = False
        if in_block and not getroffen:
            m = re.match(rf"^(\s+{re.escape(name)}\s*:\s*){zahl}(.*)$", z.rstrip("\r\n"))
            if m:
                ende = z[len(z.rstrip("\r\n")):]
                z = f"{m.group(1)}{_text(wert)}{m.group(2)}{ende}"
                getroffen = True
        neu.append(z)
    if not getroffen:
        raise SwkiFehler(f"{pfad.name}: Parameter {name} nicht gefunden (Zahl in parameter:)")
    neu_text = "".join(neu)
    if yaml.safe_load(neu_text).get("parameter", {}).get(name) != wert:
        raise SwkiFehler(f"{pfad.name}: {name} = {wert} ließ sich nicht sauber schreiben")
    pfad.write_text(neu_text, encoding="utf-8")


def _features(pfad: Path) -> list:
    return (yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}).get("features", [])


def uebernehmen(pfad: Path, basis: Path, lauf_nr: int | None, probe_nr: int | None) -> dict:
    """Gewinner (oder eine genannte Probe) eines Laufs in die Specs schreiben und im Raum freigeben."""
    from swki.optimierung.auftrag import stellschrauben
    from swki.spec.freigabe import FreigabeFehler
    if lauf_nr is None:
        kandidaten = [n for n in reversed(laeufe(basis))
                      if (basis / f"optimierung-{n}" / "status.json").is_file()
                      and json.loads((basis / f"optimierung-{n}" / "status.json").read_text(encoding="utf-8"))
                      .get("grund") == "ZIEL"]
        if not kandidaten:
            raise SwkiFehler(f"kein Lauf mit Ende ZIEL in {basis}; --lauf und --probe angeben")
        lauf_nr = kandidaten[0]
    lauf = basis / f"optimierung-{lauf_nr}"
    s = json.loads((lauf / "status.json").read_text(encoding="utf-8"))
    if probe_nr is None:
        if s["grund"] != "ZIEL" or not s.get("bester"):
            raise SwkiFehler(f"{lauf.name} endete mit {s['grund']}; ohne ZIEL nur mit --probe <nr> (Nutzer fragen)")
        probe_nr = s["bester"]["nr"]
    proben = [json.loads(z) for z in (lauf / "proben.jsonl").read_text(encoding="utf-8").splitlines()]
    probe = next((p for p in proben if p["nr"] == probe_nr), None)
    if probe is None or probe.get("status") != "simuliert":
        raise SwkiFehler(f"{lauf.name}: Probe {probe_nr} fehlt oder wurde nicht simuliert")
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    schrauben = stellschrauben(spec["optimierung"], pfad.name)
    for d in sorted({x.datei for x in schrauben if x.datei} | {pfad.name}):
        if _features(pfad.parent / d) != _features(lauf / "specs" / d):
            raise SwkiFehler(f"FORM_GEAENDERT: {d} hat nicht mehr die Form von {lauf.name} (Features geändert); "
                             "das Ergebnis gehört zu einer anderen Variante")
    geschrieben, ablauf = {}, {}
    for x in schrauben:
        if x.name not in probe["werte"]:
            continue
        if x.ablauf:
            ablauf[x.ablauf] = probe["werte"][x.name]
            continue
        w = _zahl(float(probe["werte"][x.name]), x.schritt, x.rahmen[0])
        setze_parameter(pfad.parent / x.datei, x.parameter, w)
        geschrieben.setdefault(x.datei, {})[x.parameter] = w
    quelle = f"{lauf} Probe {probe_nr} ({s['grund']}, Wert {probe['wert']})"
    erg = {"lauf": str(lauf), "probe": probe_nr, "wert": probe["wert"], "geschrieben": geschrieben,
           "ablauf": ablauf, "stufe2": s.get("bester", {}).get("stufe2") if probe_nr == (s.get("bester") or {}).get("nr")
           else None}
    try:
        from swki.optimierung.raum import freigeben_im_raum
        frei = freigeben_im_raum(pfad, quelle=quelle)
        erg.update(freigegeben=True, freigabe=frei.get("im_raum"),
                   naechster_schritt=f"swki durchlauf {pfad.name} --neustart, Prüfer, Bericht an den Nutzer "
                                     "(Ablaufgrößen an die Steuerung)" if ablauf else
                   f"swki durchlauf {pfad.name} --neustart, Prüfer, Bericht an den Nutzer")
    except FreigabeFehler as e:
        erg.update(freigegeben=False, code=e.daten.get("code"), meldung=str(e),
                   naechster_schritt="Nutzer fragen: Ergebnis liegt nicht im freigegebenen Raum")
    return erg


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("optimiere", help="Optimierungsauftrag rechnen (Schnellbau + MuJoCo + Optuna, ohne "
                                                "SolidWorks) bzw. Ergebnis übernehmen")
    p.add_argument("spec", help="Teil- oder Baugruppen-Spec mit Block optimierung")
    p.add_argument("--kerne", type=int, help="Arbeitsprozesse (Standard: Kerne − 1)")
    p.add_argument("--fortsetzen", type=int, metavar="N", help="abgebrochenen Lauf optimierung-N fortsetzen")
    p.add_argument("--arbeitsordner", help="statt <arbeitsordner> aus config/rechner.yaml (Tests)")
    p.add_argument("--uebernehmen", action="store_true",
                   help="Gewinner (Ende ZIEL) in die Specs schreiben und im Raum freigeben (Spec C2 §6)")
    p.add_argument("--lauf", type=int, help="mit --uebernehmen: Lauf optimierung-N (Standard: letzter mit ZIEL)")
    p.add_argument("--probe", type=int, help="mit --uebernehmen: diese Probe statt des Gewinners")
    p.set_defaults(func=_optimiere)
