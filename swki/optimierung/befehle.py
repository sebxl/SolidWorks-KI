"""Befehl "swki optimiere <spec>" (Spec C2 §4) und "swki optimiere <spec> --uebernehmen" (§6: Werte schreiben und
Freigabe-Vorlage; gebaut wird erst nach dem OK des Nutzers).

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
    except Exception as e:  # vor dem Start der Schleife (Prüfaufgabe nicht ladbar, Bewertung geändert): auch FEHLER
        from swki.optimierung import bericht
        s = bericht.frueher_fehler(pfad, lauf, e.detail if isinstance(e, Ende) else f"{type(e).__name__}: {e}")
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


def ersetze_parameter(text: str, name: str, wert: float, datei: str = "Spec") -> str:
    """YAML-Text mit neuem Wert eines Parameters (Kommentare bleiben); Block- oder Fluss-Schreibweise."""
    neu, in_block, getroffen = [], False, False
    zahl = r"-?[0-9][0-9_.eE+-]*"
    for z in text.splitlines(keepends=True):
        if re.match(r"^parameter:\s*\{", z):
            z2 = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(name)}(\s*:\s*){zahl}", lambda m: f"{name}{m.group(1)}{_text(wert)}",
                        z, count=1)
            getroffen = getroffen or z2 != z
            neu.append(z2)
            continue
        if re.match(r"^parameter:\s*(#.*)?$", z):
            in_block = True
        elif in_block and re.match(r"^[^\s#]", z):
            in_block = False
        if in_block and not getroffen:
            m = re.match(rf"^(\s+{re.escape(name)}\s*:\s*){zahl}(.*)$", z.rstrip("\r\n"))
            if m:
                ende = z[len(z.rstrip("\r\n")):]
                z = f"{m.group(1)}{_text(wert)}{m.group(2)}{ende}"
                getroffen = True
        neu.append(z)
    if not getroffen:
        raise SwkiFehler(f"{datei}: Parameter {name} nicht gefunden (Zahl in parameter:)")
    neu_text = "".join(neu)
    if yaml.safe_load(neu_text).get("parameter", {}).get(name) != wert:
        raise SwkiFehler(f"{datei}: {name} = {wert} ließ sich nicht sauber schreiben")
    return neu_text


def setze_parameter(pfad: Path, name: str, wert: float) -> None:
    pfad.write_text(ersetze_parameter(pfad.read_text(encoding="utf-8"), name, wert, pfad.name), encoding="utf-8")


def _lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else {}


def _raum_des_laufs(lauf: Path) -> str | None:
    return _lies(lauf / "bewertung.json").get("raum_summe")


def _stand(pfad: Path, namen: list[str]) -> dict:
    """Spec ohne Block und mit maskierten Stellschrauben (Vergleich Lauf gegen jetzt)."""
    from swki.optimierung.auftrag import maskiert
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    spec.pop("optimierung", None)
    return maskiert(spec, namen)


def _form_pruefen(pfad: Path, lauf: Path, schrauben: list) -> None:
    """Die Specs müssen dem Stand des Laufs entsprechen, außer den Stellschrauben (Features, Verknüpfungen, Parameter)."""
    haupt = yaml.safe_load((lauf / "specs" / pfad.name).read_text(encoding="utf-8"))
    dateien = {pfad.name} | {k["quelle"]["teil"] for k in haupt.get("komponenten", []) if "teil" in k.get("quelle", {})}
    for d in sorted(dateien):
        namen = [x.parameter for x in schrauben if x.datei == d]
        if _stand(pfad.parent / d, namen) != _stand(lauf / "specs" / d, namen):
            raise SwkiFehler(f"FORM_GEAENDERT: {d} hat nicht mehr den Stand von {lauf.name}; das Ergebnis gehört zu einer "
                             "anderen Variante")


def _lauf_waehlen(basis: Path, lauf_nr: int | None, raum_jetzt: str) -> Path:
    """Genannter Lauf oder der letzte mit Ende ZIEL im aktuellen Raum."""
    if lauf_nr is not None:
        lauf = basis / f"optimierung-{lauf_nr}"
        if _raum_des_laufs(lauf) != raum_jetzt:
            raise SwkiFehler(f"LAUF_ANDERER_RAUM: {lauf.name} wurde unter einem anderen Raum gerechnet (Ziel, Szenarien, "
                             "Rahmen, Prüfaufgabe oder Anforderungen geändert)")
        return lauf
    ziele = [basis / f"optimierung-{n}" for n in reversed(laeufe(basis))
             if _lies(basis / f"optimierung-{n}" / "status.json").get("grund") == "ZIEL"]
    if not ziele:
        raise SwkiFehler(f"kein Lauf mit Ende ZIEL in {basis}; --lauf und --probe angeben")
    passend = [x for x in ziele if _raum_des_laufs(x) == raum_jetzt]
    if not passend:
        raise SwkiFehler(f"LAUF_ANDERER_RAUM: {ziele[0].name} und ältere ZIEL-Läufe gehören zu einem anderen Raum; neu "
                         "rechnen")
    return passend[0]


def uebernehmen(pfad: Path, basis: Path, lauf_nr: int | None, probe_nr: int | None) -> dict:
    """Gewinner (oder eine genannte zulässige Probe) eines Laufs prüfen, in die Specs schreiben und die Freigabe-Vorlage
    anlegen. Gibt nichts frei: gebaut wird erst nach dem OK des Nutzers (Spec C2 §6)."""
    from swki.optimierung import bericht
    from swki.optimierung.auftrag import stellschrauben
    from swki.optimierung.raum import pruefe_im_raum, raum_summe_datei
    from swki.spec.freigabe import FreigabeFehler
    lauf = _lauf_waehlen(basis, lauf_nr, raum_summe_datei(pfad))
    s = _lies(lauf / "status.json")
    if probe_nr is None:
        if s["grund"] != "ZIEL" or not s.get("bester"):
            raise SwkiFehler(f"{lauf.name} endete mit {s['grund']}; ohne ZIEL nur mit --probe <nr> (Nutzer fragen)")
        probe_nr = s["bester"]["nr"]
    proben = [json.loads(z) for z in (lauf / "proben.jsonl").read_text(encoding="utf-8").splitlines()]
    probe = next((p for p in proben if p["nr"] == probe_nr), None)
    if probe is None or probe.get("status") != "simuliert":
        raise SwkiFehler(f"{lauf.name}: Probe {probe_nr} fehlt oder wurde nicht simuliert")
    stufe2 = _lies(lauf / "zustand.json").get("stufe2", {}).get(str(probe_nr), {})
    if not probe.get("zulaessig") or stufe2.get("abgewertet"):
        raise SwkiFehler(f"PROBE_NICHT_ZULAESSIG: {lauf.name} Probe {probe_nr} verletzt eine Nebenbedingung oder fiel in "
                         "Prüfstufe 2 durch")
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    schrauben = stellschrauben(spec["optimierung"], pfad.name)
    _form_pruefen(pfad, lauf, schrauben)
    try:
        pruefe_im_raum(pfad)
        raum_frei = True
    except FreigabeFehler as e:
        if e.daten.get("code") != "RAUM_FEHLT":      # Kopie, Form oder Werte: nichts schreiben, Nutzer fragen
            raise
        raum_frei = False
    texte, geschrieben, ablauf = {}, {}, {}
    for x in schrauben:
        if x.name not in probe["werte"]:
            continue
        if x.ablauf:
            ablauf[x.ablauf] = probe["werte"][x.name]
            continue
        w = _zahl(float(probe["werte"][x.name]), x.schritt, x.rahmen[0])
        ziel = pfad.parent / x.datei
        texte[ziel] = ersetze_parameter(texte.get(ziel, ziel.read_text(encoding="utf-8")), x.parameter, w, x.datei)
        geschrieben.setdefault(x.datei, {})[x.parameter] = w
    for ziel, text in texte.items():                 # erst alles prüfen, dann schreiben
        ziel.write_text(text, encoding="utf-8")
    nachweis = pruefe_im_raum(pfad) if raum_frei else None
    quelle = f"{lauf} Probe {probe_nr} ({s['grund']}, Wert {probe['wert']})"
    vorlage = lauf / "freigabe_vorlage.md"
    vorlage.write_text(bericht.freigabe_vorlage(s, probe, pfad.name, geschrieben, nachweis, ablauf), encoding="utf-8")
    return {"lauf": str(lauf), "probe": probe_nr, "wert": probe["wert"], "geschrieben": geschrieben, "ablauf": ablauf,
            "stufe2": stufe2 or None, "freigegeben": False, "raum_freigegeben": raum_frei, "quelle": quelle,
            "freigabe_vorlage": str(vorlage),
            "naechster_schritt": "Freigabe-Vorlage dem Nutzer zeigen. Erst nach seinem ausdrücklichen OK: swki freigeben "
                                 f"{pfad.name}{' --im-raum --quelle <quelle>' if raum_frei else ''}, dann swki durchlauf "
                                 f"{pfad.name} --neustart, Prüfer, Bericht."}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("optimiere", help="Optimierungsauftrag rechnen (Schnellbau + MuJoCo + Optuna, ohne "
                                                "SolidWorks) bzw. Ergebnis übernehmen")
    p.add_argument("spec", help="Teil- oder Baugruppen-Spec mit Block optimierung")
    p.add_argument("--kerne", type=int, help="Arbeitsprozesse (Standard: Kerne − 1)")
    p.add_argument("--fortsetzen", type=int, metavar="N", help="abgebrochenen Lauf optimierung-N fortsetzen")
    p.add_argument("--arbeitsordner", help="statt <arbeitsordner> aus config/rechner.yaml (Tests)")
    p.add_argument("--uebernehmen", action="store_true",
                   help="Gewinner (Ende ZIEL) in die Specs schreiben und Freigabe-Vorlage anlegen; gibt nichts frei "
                        "(Spec C2 §6)")
    p.add_argument("--lauf", type=int, help="mit --uebernehmen: Lauf optimierung-N (Standard: letzter mit ZIEL)")
    p.add_argument("--probe", type=int, help="mit --uebernehmen: diese Probe statt des Gewinners")
    p.set_defaults(func=_optimiere)
