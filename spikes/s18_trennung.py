"""Spike S18, Trennung: RPC_E_DISCONNECTED im ersten Bau nach `sw_neustart` nachstellen und die Stelle belegen.

Eine Reihe startet je Versuch (wahlweise) SolidWorks neu und ruft dann in einem eigenen Prozess mit Zeitlimit genau einen Fall auf.
Jeder Versuch hängt eine JSON-Zeile an `<arbeitsordner>/SPIKE-TRENNUNG/trace.jsonl`: Status, Traceback, die letzten COM-Zugriffe,
Zeiten, Private Bytes. Gearbeitet wird an einer Kopie des Musters im Arbeitsordner, das Muster bleibt unberührt.

Ursache und Messungen: docs/bestandsdateien/ergebnisse.md, „Trennung: Ursache“. Seit der Behebung bricht `voll` nicht mehr ab, den alten Weg stellt `voll_alt` nach.

  python spikes/s18_trennung.py reihe --fall voll_alt --n 12 [--ohne-neustart] [--zeit 180]
  python spikes/s18_trennung.py einzel --fall voll_wache

`*_wache`: fragt vor jedem weiteren COM-Zugriff die Skizzenfläche und nennt den Aufruf, der sie trennte. `min`: Folge ohne Skizzierer.
"""

import argparse
import collections
import contextlib
import json
import shutil
import stat
import subprocess
import sys
import time
import traceback
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

import yaml  # noqa: E402

from swki.compiler.protokoll import Protokoll  # noqa: E402
from swki.konfig import lade_rechner, lade_standard  # noqa: E402
from werkzeuge.sw_neustart import instanzen, neustart, sw_privat_mb  # noqa: E402

REFERENZ = WURZEL / "tests" / "referenz" / "bestand"
SPEC = REFERENZ / "lagerdeckel_rev.yaml"
MUSTER = REFERENZ / "muster" / "Lagerdeckel.SLDPRT"
AUFTRAG = "SPIKE-TRENNUNG"
RPC_E_DISCONNECTED = -2147417848
WARTEZEITEN = (0.0, 0.0)


def ordner() -> Path:
    o = lade_rechner().arbeitsordner / AUFTRAG
    o.mkdir(parents=True, exist_ok=True)
    return o


def schreibe(zeile: dict) -> None:
    with (ordner() / "trace.jsonl").open("a", encoding="utf-8") as d:
        d.write(json.dumps(zeile, ensure_ascii=False, default=str) + "\n")


class Spur:
    """Ringpuffer der COM-Zugriffe im Late Binding: jeder Member läuft über CDispatch.__getattr__ (auch gebaute Methoden)."""

    def __init__(self, laenge: int = 240):
        self.ring = collections.deque(maxlen=laenge)
        self.beginn = time.monotonic()
        self.bewacht, self.gestorben, self.zuletzt = None, None, None
        self.lange, self.vorher, self.letzter, self.fenster = [], 0.0, "", False  # lange Aufrufe ab der bewachten Fläche

    def an(self) -> None:
        from win32com.client import dynamic
        original = dynamic.CDispatch.__getattr__

        def getattr_mit_spur(obj, attr):
            if not attr.startswith("_"):
                jetzt = time.monotonic() - self.beginn
                if jetzt - self.vorher > 0.15 and self.fenster:
                    self.lange.append((self.letzter, round(jetzt - self.vorher, 3)))
                self.vorher, self.letzter = jetzt, attr
                self.ring.append(f"{jetzt:8.3f} {id(obj) & 0xffffff:06x}.{attr}")
                self.wache(original, attr)
            return original(obj, attr)

        dynamic.CDispatch.__getattr__ = getattr_mit_spur

    def wache(self, original, attr: str) -> None:
        """Fragt vor jedem weiteren COM-Zugriff das bewachte Objekt: Der erste Fehlschlag grenzt den Aufruf ein, der es trennte."""
        import pythoncom
        if self.bewacht is None or self.gestorben is not None:
            return
        objekt, self.bewacht = self.bewacht, None  # keine Rekursion über die Spur
        try:
            original(objekt, "GetBox")
            self.bewacht = objekt
            self.zuletzt = attr
        except pythoncom.com_error as e:
            self.gestorben = {"hresult": e.hresult, "zuletzt_lebend_vor": self.zuletzt, "tot_vor": attr,
                              "t": round(time.monotonic() - self.beginn, 3)}


def kopie(lauf: str) -> Path:
    ziel = ordner() / lauf / MUSTER.name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MUSTER, ziel)
    ziel.chmod(stat.S_IWRITE | stat.S_IREAD)
    return ziel


def wache_an(spur: Spur) -> None:
    from swki.compiler.handler import normbohrung as modul
    original = modul.skizzenebene_nach_bohrung

    def mit_wache(ctx, f, se):
        neu = original(ctx, f, se)
        spur.bewacht, spur.fenster = neu.flaeche.objekt, True
        return neu

    modul.skizzenebene_nach_bohrung = mit_wache


def alter_weg() -> None:
    """Stand vor der Behebung: Die Ebene wird vor dem Öffnen der Skizze geholt. Nur so ist der Abbruch noch nachzustellen."""
    from swki.compiler.handler import normbohrung as modul
    original = modul.positionen_festlegen

    def festlegen(ctx, feature, ebene, *rest):
        se = ebene()
        original(ctx, feature, lambda: se, *rest)

    modul.positionen_festlegen = festlegen


def fall_teil(fall: str, spur: Spur, zeile: dict) -> None:
    """Neues Teil wie swki bauen (mit sw.schnell), Klotz und Normbohrung mit Randbezug: keine Fremddatei, keine Punkte davor."""
    from swki.compiler import sw
    from swki.compiler.ablauf import baue_features
    from swki.compiler.kontext import Kontext
    from swki.compiler.registry import alle_handler
    from swki.verbindung import verbinde

    wache_an(spur)
    spec = {"art": "teil", "name": "T", "parameter": {"L": 100, "B": 60, "RA": 12, "ZG": 24}, "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B", "bezug": {"u": "mitte", "v": "mitte"}}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+RA", "=ZG"], ["=-L/2+RA", "=-ZG"]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10, "gewindetiefe": 8}]}
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    spur.an()
    model = sw.neues_teil(app, r.vorlage_teil)
    protokoll = Protokoll(AUFTRAG, "teil.yaml", 1, r.sw_jahr)
    fehler = None
    try:
        ctx = Kontext(app, model, spec, Path("teil.yaml"), 0.1, gleichungen=False)
        with sw.schnell(app, model):
            fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    finally:
        sw.schliesse(app, model)
    zeile["knoten"], zeile["gestorben"], zeile["lange"] = [(k.id, k.status) for k in protokoll.knoten], spur.gestorben, spur.lange
    if fehler is not None:
        raise fehler


def fall_bau(fall: str, spur: Spur, zeile: dict) -> None:
    """Wie swki.bestand.bau.bauen ohne Freigabe und Lauf-Verwaltung, nur an der Kopie im Spike-Ordner."""
    from swki.bestand import bau
    from swki.compiler import sw
    from swki.pruefung.messen import oeffne
    from swki.verbindung import verbinde

    if "wache" in fall:
        wache_an(spur)
    if "ohne_schnell" in fall:
        sw.schnell = lambda app, model: contextlib.nullcontext()
    if "alt" in fall:
        alter_weg()
    r = lade_rechner()
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    if fall.startswith("nur_p5"):
        spec["punkte"] = [p for p in spec["punkte"] if p["id"] == "p5"]
    aufnahme = json.loads((REFERENZ / "bestand.json").read_text(encoding="utf-8"))
    pfad = kopie(f"lauf-{int(time.time())}")
    protokoll = Protokoll(AUFTRAG, SPEC.name, 1, r.sw_jahr)
    app = verbinde(r.sw_jahr)
    spur.an()
    model = oeffne(app, pfad)
    fehler = None
    try:
        fehler = bau._aendere_und_speichere(app, model, spec, SPEC, lade_standard()["toleranzen"]["anker_mm"], aufnahme, protokoll, pfad)
    finally:
        zeile["dokumente_offen_ende"] = app.GetDocumentCount
        sw.schliesse(app, model)
    zeile["knoten"], zeile["gestorben"], zeile["lange"] = [(k.id, k.status) for k in protokoll.knoten], spur.gestorben, spur.lange
    if fehler is not None:
        raise fehler


def probe(objekt, member: str) -> str:
    """Anzahl aus einem Listen-Member oder „getrennt“: Das Objekt wird nur hier angefasst."""
    import pythoncom
    try:
        return len(getattr(objekt, member) or ())
    except pythoncom.com_error as e:
        return "getrennt" if e.hresult == RPC_E_DISCONNECTED else f"com {e.hresult}"


def bohrung_und_skizze(model, warte_s: float) -> dict:
    """Kleinste Folge ohne Skizzierer: Fläche holen, HoleWizard5, Fläche neu holen, Positionsskizze öffnen, warten, Fläche fragen."""
    from types import SimpleNamespace

    from swki.compiler import sw
    from swki.compiler.handler.normbohrung import hole_werte
    from swki.compiler.skizze import positionsskizze
    from swki.compiler.topologie import koerper, loese_flaeche
    from swki.spec.normen import SW_ART, SW_BEFESTIGUNG, SW_END_BLIND, SW_NORM, norm_von, normmasse
    from swki.verbindung import mm

    c = SimpleNamespace(model=model, wert=lambda v: v, tol_mm=0.01)
    anker = {"nahe": [45, 0, 20]}
    vor_bohrung = loese_flaeche(c, anker)
    d: dict = {"warte_s": warte_s, "kanten_vor": probe(vor_bohrung.objekt, "GetEdges")}
    sw.auswahl_leeren(model)
    if not model.Extension.SelectByRay(mm(-38), mm(24), mm(21), 0, 0, -1, 0.0005, 2, False, 0, 0):
        raise RuntimeError("Strahl trifft nicht")
    f = {"art": "gewinde", "groesse": "M6"}
    norm, masse = norm_von(f), normmasse("gewinde", "M6", norm_von(f))
    feature = model.FeatureManager.HoleWizard5(SW_ART["gewinde"], SW_NORM[norm], SW_BEFESTIGUNG["gewinde"], masse["sw_groesse"], SW_END_BLIND,
                                               -1, mm(10), -1, *hole_werte("gewinde", mm(8)), "", False, False, True, False, True, False)
    sw.auswahl_leeren(model)
    d["nach_bohrung_alt"] = probe(vor_bohrung.objekt, "GetEdges")
    nach_bohrung = loese_flaeche(c, anker)
    d["kanten_nach"] = probe(nach_bohrung.objekt, "GetEdges")
    d["flaechen_nach"] = sum(len(b.GetFaces() or ()) for b in koerper(model))
    skizze = positionsskizze(feature)
    skizze.Select2(False, 0)
    sm = model.SketchManager
    sm.InsertSketch(True)
    try:
        d["flaechen_in_skizze"] = sum(len(b.GetFaces() or ()) for b in koerper(model))
        time.sleep(warte_s)
        d["in_skizze_alt"] = probe(nach_bohrung.objekt, "GetEdges")
        d["in_skizze_vor"] = probe(vor_bohrung.objekt, "GetEdges")
        d["in_skizze_frisch"] = probe(loese_flaeche(c, anker).objekt, "GetEdges")
    finally:
        sm.InsertSketch(True)
    d["danach_alt"] = probe(nach_bohrung.objekt, "GetEdges")
    return d


def fall_min(fall: str, spur: Spur, zeile: dict) -> None:
    """In einer Sitzung je Wartezeit eine frische Kopie: bohrung_und_skizze."""
    from swki.compiler import sw
    from swki.pruefung.messen import oeffne
    from swki.verbindung import verbinde

    app = verbinde(lade_rechner().sw_jahr)
    spur.an()
    zeile["proben"] = []
    for warte_s in WARTEZEITEN:
        model = oeffne(app, kopie(f"lauf-{int(time.time() * 10)}"))
        try:
            zeile["proben"].append(bohrung_und_skizze(model, warte_s))
        finally:
            sw.schliesse(app, model)


FAELLE = {"voll": fall_bau, "voll_wache": fall_bau, "voll_alt": fall_bau, "voll_alt_wache": fall_bau, "nur_p5_wache": fall_bau,
          "voll_wache_ohne_schnell": fall_bau, "teil_wache": fall_teil, "min": fall_min}


def einzel(fall: str, nummer: str) -> int:
    zeile: dict = {"fall": fall, "nummer": nummer, "start": time.strftime("%H:%M:%S"), "pids": instanzen(), "mb_vorher": sw_privat_mb()}
    spur = Spur()
    beginn = time.monotonic()
    try:
        FAELLE[fall](fall, spur, zeile)
        zeile["status"] = "ok"
    except Exception as e:
        zeile |= {"status": "fehler", "typ": type(e).__name__, "meldung": str(e)[:400],
                  "hresult": getattr(e, "hresult", None), "traceback": traceback.format_exception(e)}
    zeile |= {"s": round(time.monotonic() - beginn, 2), "mb_nachher": sw_privat_mb(), "spur": list(spur.ring)}
    schreibe(zeile)
    print(json.dumps({k: v for k, v in zeile.items() if k not in ("spur", "traceback")}, ensure_ascii=False, default=str))
    return 0 if zeile["status"] == "ok" else 1


def reihe(fall: str, n: int, mit_neustart: bool, zeit: int) -> None:
    for i in range(n):
        info = neustart() if mit_neustart else None
        nummer = f"{fall}-{int(time.time())}-{i}"
        try:
            aus = subprocess.run([sys.executable, __file__, "einzel", "--fall", fall, "--nummer", nummer], cwd=WURZEL,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=zeit)
            ergebnis = f"exit {aus.returncode}"
            print(aus.stdout.strip()[-400:] or aus.stderr.strip()[-800:], flush=True)
        except subprocess.TimeoutExpired:
            ergebnis = "zeitlimit"
            schreibe({"fall": fall, "nummer": nummer, "status": "zeitlimit"})
        print(json.dumps({"versuch": i, "fall": fall, "neustart": info, "ergebnis": ergebnis}, ensure_ascii=False), flush=True)
        if ergebnis == "zeitlimit":
            break


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("art", choices=["reihe", "einzel"])
    p.add_argument("--fall", default="voll")
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--ohne-neustart", action="store_true")
    p.add_argument("--zeit", type=int, default=180)
    p.add_argument("--nummer", default="")
    a = p.parse_args()
    if a.art == "einzel":
        sys.exit(einzel(a.fall, a.nummer))
    reihe(a.fall, a.n, not a.ohne_neustart, a.zeit)


if __name__ == "__main__":
    main()
