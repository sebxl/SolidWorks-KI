"""S10c (Nachtrag AP 6.8, 10.10.2026): Normmaße des Bohrungsassistenten für M4 → swki/wissen/bohrungsnormen.yaml.

Gleiches Verfahren wie S10 Frage 3 (spikes/s10_f3_normmasse.py) und S10b, nur für die neuen Größen: Gewinde M4
(Festo ADNGF-16-25 Befestigung, Effilux EFFI-SBL) und Zylinderschraube M4. Schreibweise wie in S10 Frage 1 für M5 … M16
(Größe ohne Steigung). Ergebnis: docs/stufe0/ergebnisse/s10c_m4.json (messungen, tabelle, abgleich).
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import start
from spikes.s10_f3_normmasse import DICKE_MM, GEWINDETIEFE_MM, TIEFE_MM, _messen, vorschlag
from spikes.s10_gemeinsam import soll_volumen

GROESSEN = {"gewinde": {"M4": "M4"}, "zylinderschraube": {"M4": "M4"}}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"groessen": GROESSEN, "tiefe_mm": TIEFE_MM, "gewindetiefe_mm": GEWINDETIEFE_MM,
               "messungen": {}, "tabelle": {}, "abgleich": {}}
    for art, groessen in GROESSEN.items():
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
    lauf("s10c_m4", pruefen)
