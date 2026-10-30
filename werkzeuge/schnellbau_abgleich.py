"""Referenz-Suite durch beide Backends (Spec C1 §4.2): SolidWorks baut und prüft jede Referenz, der Schnellbau baut
dieselben Teil-Specs; Vergleich je Eigenteil (Volumen und Hüllquader aus dem Prüfbericht, STL mit
werkzeuge/messstand/vergleich.py). Schreibt die SolidWorks-Messwerte nach tests/schnellbau/sw_referenz.json – die
Sollwerte von tests/schnellbau/test_referenz.py ohne SolidWorks.

Ablauf je Referenz (Liste wie tests/referenz/test_referenzen.py): Ordner nach <arbeitsordner>/SCHNELLBAU-ABGLEICH/
SBREF-<ordner> kopieren (Auftrag SBREF-<ordner>), `swki durchlauf --freigeben --neustart` (frisches SolidWorks vor Bauen
und Prüfen; die Freigabe betrifft nur diese Kopie, wie in der Regressions-Suite), STL je Eigenteil (Teil: geometrie.STL
des Laufs, Baugruppe: Export der Teildatei), Schnellbau der Teil-Spec, Vergleich.

Aufruf (SolidWorks frei, keine andere Sitzung mit SolidWorks): .venv\\Scripts\\python.exe -m werkzeuge.schnellbau_abgleich
        [--nur buchse,stehlager] [--ohne-json]
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from swki.auftrag import lauf_ordner
from swki.konfig import PROJEKT, lade_rechner

REFERENZEN = [("buchse", "buchse.yaml"), ("formplatte", "formplatte_ds.yaml"),
              ("auswerferhalteplatte", "auswerferhalteplatte.yaml"), ("stehlager", "stehlager.yaml"),
              ("schlitten", "linearschlitten.yaml"), ("zahnstangentrieb", "zahnstange.yaml"),
              ("zahnstangentrieb", "ritzelwelle.yaml"), ("zahnstangentrieb", "antriebswelle.yaml"),
              ("zahnstangentrieb", "zahnstangentrieb.yaml"), ("motorhalter", "motorhalter.yaml"),
              ("zentrieraufnahme", "zentrieraufnahme.yaml")]
QUELLE = PROJEKT / "tests" / "referenz"
SW_REFERENZ = PROJEKT / "tests" / "schnellbau" / "sw_referenz.json"


def _sw_werte(bericht: dict, komponente: str | None) -> dict:
    """Volumen/Hüllquader eines Teils (komponente None) oder einer Komponente aus dem Prüfbericht."""
    out = {}
    for p in bericht.get("pruefungen", []):
        name, _, was = p["id"].rpartition(": ") if ": " in p["id"] else ("", "", p["id"])
        if (komponente is None and name == "") or name == komponente:
            if was in ("volumen", "huellquader"):
                out[was] = p["ist"]
    return out


def _teile(ordner: Path, spec_datei: str) -> list[tuple[str | None, str]]:
    """[(komponente oder None, Teil-Spec-Datei)] einer Referenz-Spec; je Teil-Spec nur einmal."""
    import yaml
    spec = yaml.safe_load((ordner / spec_datei).read_text(encoding="utf-8"))
    if spec.get("art") == "teil":
        return [(None, spec_datei)]
    gesehen, out = set(), []
    for k in spec["komponenten"]:
        datei = k["quelle"].get("teil")
        if datei and datei not in gesehen:
            gesehen.add(datei)
            out.append((k["id"], datei))
    return out


def abgleich(ordner_name: str, spec_datei: str, wurzel: Path) -> dict:
    from swki.durchlauf import durchlauf
    from swki.schnellbau.befehle import exportiere_stl
    from swki.schnellbau.fehler import SchnellbauFehler
    from swki.schnellbau.teil import baue, lade
    from werkzeuge.messstand.stl_export import exportiere
    from werkzeuge.messstand.vergleich import vergleiche

    auftrag = wurzel / f"SBREF-{ordner_name}"
    if not auftrag.exists():
        shutil.copytree(QUELLE / ordner_name, auftrag)
    spec_pfad = auftrag / spec_datei
    t0 = time.perf_counter()
    d = durchlauf(spec_pfad, freigeben=True, neustart=True)
    erg = {"referenz": f"{ordner_name}/{spec_datei}", "schritt": d.get("schritt"), "lauf": d.get("lauf"),
           "sw_s": round(time.perf_counter() - t0, 1), "teile": []}
    if d.get("schritt") != "fertig":
        erg["fehler"] = d.get("fehler") or d.get("meldung") or d.get("code")
        return erg
    r = lade_rechner()
    lauf = lauf_ordner(r, auftrag.name, d["lauf"])
    bericht = json.loads((lauf / "pruefbericht.json").read_text(encoding="utf-8"))
    for komp, datei in _teile(auftrag, spec_datei):
        spec = lade(auftrag / datei)
        z = {"spec": f"{ordner_name}/{datei}", "komponente": komp, **_sw_werte(bericht, komp)}
        if komp is None:
            sw_stl = lauf / "geometrie.STL"
        else:
            sw_stl = lauf / "stl" / f"{Path(datei).stem}.stl"
            exportiere(lauf / f"{auftrag.name}_{spec['name']}.SLDPRT", sw_stl)
        t1 = time.perf_counter()
        try:
            teil = baue(spec)
        except SchnellbauFehler as e:
            z["schnellbau"] = {"fehler": str(e), "code": e.code}
            erg["teile"].append(z)
            continue
        bb = teil.solid.bounding_box()
        sb_stl = exportiere_stl(teil.solid, lauf / "schnellbau" / f"{Path(datei).stem}.stl")
        v = vergleiche(sb_stl, sw_stl)
        z["schnellbau"] = {"volumen": round(teil.solid.volume, 6), "huellquader": [bb.size.X, bb.size.Y, bb.size.Z],
                           "ms": round((time.perf_counter() - t1) * 1000, 1)}
        z["stl"] = {"richtig": v["richtig"], "gespiegelt": v["gespiegelt"],
                    **{k: v["beste"][k] for k in ("p99_mm", "max_mm", "mittel_mm") if k in v["beste"]}}
        if "volumen" in z:
            z["volumen_abw_prozent"] = round(100 * (teil.solid.volume - z["volumen"]) / z["volumen"], 6)
        erg["teile"].append(z)
    return erg


def schreibe_sollwerte(alle: list[dict]) -> dict:
    """SolidWorks-Messwerte (Volumen und/oder Hüllquader) je Teil-Spec nach SW_REFERENZ; Teile, die der Schnellbau
    nicht kann (skript), bleiben draußen."""
    werte = json.loads(SW_REFERENZ.read_text(encoding="utf-8")) if SW_REFERENZ.exists() else {}
    for e in alle:
        for z in e["teile"]:
            if "fehler" in z.get("schnellbau", {}) or not ("volumen" in z or "huellquader" in z):
                continue
            werte[z["spec"].removesuffix(".yaml")] = {"spec": z["spec"], **{k: z[k] for k in ("volumen", "huellquader")
                                                                              if k in z},
                                                       "quelle": f"SolidWorks {e['referenz']} lauf-{e['lauf']}"}
    SW_REFERENZ.write_text(json.dumps(dict(sorted(werte.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return werte


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nur", help="Ordner der Referenzen, Komma-getrennt")
    ap.add_argument("--ohne-json", action="store_true", help="tests/schnellbau/sw_referenz.json nicht schreiben")
    ap.add_argument("--aus-ergebnis", action="store_true",
                    help="ohne SolidWorks: sw_referenz.json aus dem letzten ergebnis.json neu schreiben")
    a = ap.parse_args()
    nur = set(a.nur.split(",")) if a.nur else None
    wurzel = lade_rechner().arbeitsordner / "SCHNELLBAU-ABGLEICH"
    wurzel.mkdir(parents=True, exist_ok=True)
    if a.aus_ergebnis:
        werte = schreibe_sollwerte(json.loads((wurzel / "ergebnis.json").read_text(encoding="utf-8")))
        print(json.dumps({"sw_referenz": str(SW_REFERENZ), "teile": len(werte)}, ensure_ascii=False))
        return 0
    alle = []
    for ordner_name, spec_datei in REFERENZEN:
        if nur and ordner_name not in nur:
            continue
        e = abgleich(ordner_name, spec_datei, wurzel)
        alle.append(e)
        print(json.dumps(e, ensure_ascii=False), flush=True)
    (wurzel / "ergebnis.json").write_text(json.dumps(alle, indent=1, ensure_ascii=False), encoding="utf-8")
    if not a.ohne_json:
        schreibe_sollwerte(alle)
    fehler = [e for e in alle if e.get("fehler")]
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
