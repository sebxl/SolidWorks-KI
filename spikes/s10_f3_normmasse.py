"""S10 Frage 3: Maße, die der Bohrungsassistent je Größe erzeugt → swki/wissen/bohrungsnormen.yaml.

Für jede Größe mit Schreibweise aus Frage 1 (gewinner in docs/stufe0/ergebnisse/s10_f1_bohrungsassistent.json) im
Prüfblock 60 × 60 × 30: durch alles und blind 20 (Gewinde: Gewindetiefe 12). Gemessen: Zylinder-Radien, Kegel,
Box der Flächen, Volumenabnahme; gelesen: IWizardHoleFeatureData2. Daraus je Größe ein Tabellenvorschlag und der
Abgleich mit der Formel soll_volumen (Tiefe ab Fläche, Bohrspitze 118° nur bei blind):
- gewinde: kernloch = 2·r (Zylinder)
- zylinderschraube: durchgang = 2·r_min, senkung_d = 2·r_max, senkung_t = Deckfläche − Unterkante des großen Zylinders
- senkschraube: durchgang = 2·r_min, senkung_d = X-Ausdehnung der Kegelfläche, senkwinkel aus der Kegelhöhe
- stift: durchmesser = 2·r
"""

import json
import math

from spikes._gemeinsam import ERGEBNISSE, lauf
from spikes.s9a_gemeinsam import kasten_oben, start, teil, volumen_mm3
from spikes.s10_gemeinsam import DICKE_MM, bohrung, daten, geometrie, soll_volumen

TIEFE_MM, GEWINDETIEFE_MM = 20.0, 12.0


def _messen(app, r, art, text, blind: bool) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 60, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        kw = {"tiefe_mm": TIEFE_MM, "gewindetiefe_mm": GEWINDETIEFE_MM if art == "gewinde" else None} if blind else {}
        _, f = bohrung(model, art, text, [(0.0, 0.0)], **kw)
        if f is None:
            return {"fehler": "kein Feature"}
        return {"abnahme_mm3": round(v0 - volumen_mm3(model), 4), "geometrie": geometrie(f), "daten": daten(f)}


def vorschlag(art: str, text: str, durch: dict) -> dict:
    zylinder = durch["geometrie"]["zylinder"]
    r_min, r_max = min(z["r"] for z in zylinder), max(z["r"] for z in zylinder)
    m: dict = {"sw_groesse": text}
    if art == "gewinde":
        m["kernloch"] = round(2 * r_min, 4)
    elif art == "stift":
        m["durchmesser"] = round(2 * r_min, 4)
    elif art == "zylinderschraube":
        gross = next(z for z in zylinder if z["r"] == r_max)
        m |= {"durchgang": round(2 * r_min, 4), "senkung_d": round(2 * r_max, 4),
              "senkung_t": round(DICKE_MM - gross["box"][1], 4)}
    else:
        box = durch["geometrie"]["kegel"][0]["box"]
        ds, h = box[3] - box[0], DICKE_MM - box[1]
        m |= {"durchgang": round(2 * r_min, 4), "senkung_d": round(ds, 4),
              "senkwinkel": round(2 * math.degrees(math.atan((ds / 2 - r_min) / h)), 4)}
    gelesen = durch["daten"].get("FastenerSize")
    if isinstance(gelesen, str) and gelesen != text:
        m["gelesen"] = gelesen
    return m


def pruefen() -> dict:
    r, app = start()
    gewinner = json.loads((ERGEBNISSE / "s10_f1_bohrungsassistent.json").read_text(encoding="utf-8"))["gewinner"]
    d: dict = {"messungen": {}, "tabelle": {}, "abgleich": {}}
    for art, groessen in gewinner.items():
        for groesse, text in groessen.items():
            durch, blind = _messen(app, r, art, text, False), _messen(app, r, art, text, True)
            d["messungen"][f"{art} {groesse}"] = {"durch": durch, "blind": blind}
            if "fehler" in durch or "fehler" in blind:
                continue
            m = vorschlag(art, text, durch)
            d["tabelle"].setdefault(art, {})[groesse] = m
            soll_durch = soll_volumen(art, m, None, DICKE_MM)
            soll_blind = soll_volumen(art, m, TIEFE_MM, DICKE_MM)
            d["abgleich"][f"{art} {groesse}"] = {
                "durch_ist": durch["abnahme_mm3"], "durch_soll": round(soll_durch, 4),
                "blind_ist": blind["abnahme_mm3"], "blind_soll": round(soll_blind, 4),
                "passt": abs(durch["abnahme_mm3"] - soll_durch) <= 1e-3 * soll_durch
                and abs(blind["abnahme_mm3"] - soll_blind) <= 1e-3 * soll_blind,
            }
    return d


if __name__ == "__main__":
    lauf("s10_f3_normmasse", pruefen)
