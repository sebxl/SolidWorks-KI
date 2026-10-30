"""S18 M1/M2a: Schnellbau-Zeit je Teil (kalt/warm) und Abgleich mit SolidWorks lauf-28 ohne SolidWorks: Volumen und
Hüllquader aus dem Prüfbericht (`<teil>: volumen`, `<teil>: huellquader`, gemessen von swki pruefen in SolidWorks).

Aufruf: .venv-sim\\Scripts\\python.exe -m spikes.s18_m1_teile <auftragsordner> <pruefbericht.json> [ausgabe.json]
"""

import json
import sys
import time
from pathlib import Path

T0 = time.perf_counter()
from spikes.s18_schnellbau import baue_teil, lade  # noqa: E402  (Importzeit gehört zur Kaltmessung)
IMPORT_S = time.perf_counter() - T0

TEILE = {   # Komponente im Prüfbericht → Teil-Spec
    "rutsche": "rutsche", "weichenkeil": "weichenkeil", "schieber": "schieber", "pruefkanal": "pruefkanal",
    "klemmleiste_links": "klemmleiste", "saphirglas": "saphirglas", "zwischenplatte": "zwischenplatte",
    "durchlicht": "durchlicht_effilux", "rutschentraeger": "rutschentraeger", "durchlichtlasche": "durchlichtlasche",
}


def sw_werte(bericht: dict) -> dict:
    out = {}
    for p in bericht["pruefungen"]:
        name, _, was = p["id"].partition(": ")
        if was in ("volumen", "huellquader"):
            out.setdefault(name, {})[was] = p["ist"]
    return out


def main():
    ordner, bericht = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    sw = sw_werte(bericht)
    zeilen = []
    for komp, datei in TEILE.items():
        spec = lade(ordner / f"{datei}.freigegeben.yaml")
        zeiten = []
        for _ in range(3):
            t = time.perf_counter()
            teil = baue_teil(spec)
            zeiten.append(time.perf_counter() - t)
        ohne = baue_teil(spec, bohrungen=False)
        bb = teil.solid.bounding_box()
        groesse = [round(bb.size.X, 6), round(bb.size.Y, 6), round(bb.size.Z, 6)]
        v_sw, h_sw = sw.get(komp, {}).get("volumen"), sw.get(komp, {}).get("huellquader")
        z = dict(teil=komp, spec=datei, ms_kalt=round(zeiten[0] * 1000, 1), ms_warm=round(min(zeiten[1:]) * 1000, 1),
                 ms_ohne_bohrungen=round(ohne.sekunden * 1000, 1),
                 volumen=round(teil.solid.volume, 3), volumen_sw=v_sw,
                 volumen_abw_prozent=None if v_sw is None else round(100 * (teil.solid.volume - v_sw) / v_sw, 5),
                 huelle=groesse, huelle_sw=h_sw,
                 huelle_abw_mm=None if h_sw is None else round(max(abs(a - b) for a, b in zip(groesse, h_sw)), 6))
        zeilen.append(z)
        print(f"{komp:18s} kalt {z['ms_kalt']:7.1f} ms  warm {z['ms_warm']:6.1f} ms  "
              f"V {z['volumen']:11.3f} SW {v_sw}  Δ {z['volumen_abw_prozent']} %  Hülle Δ {z['huelle_abw_mm']} mm")
    erg = dict(import_s=round(IMPORT_S, 2), teile=zeilen,
               summe_warm_ms=round(sum(z["ms_warm"] for z in zeilen), 1))
    print(f"Import {erg['import_s']} s, Summe warm {erg['summe_warm_ms']} ms")
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(json.dumps(erg, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
