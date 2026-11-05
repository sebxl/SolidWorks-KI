"""S19 Zeile e3: Einzelbefund aus Zeile e wiederholen (Task 12 Step 3, Folge 7): „Nach `ModifyDefinition` ist `Hub` in Standard
unterdrückt“ (T9.27, eine Messung). Drei Fälle an je einer frischen beschreibbaren Kopie der Hubeinheit unter
<arbeitsordner>/S19/, Baugruppe mit Fenster wie im Bau (`spikes.s19_baugruppe.arbeit`):

- `roh`: `GetDefinition`, `MaximumDistance` 25 → 30 mm, `ModifyDefinition(daten, asm, callout_leer())` einmal in der aktiven
  Konfiguration, kein Umschalten dazwischen.
- `roh_andere`: dasselbe, vorher auf „Ohne Antrieb“ geschaltet.
- `handler`: `verknuepfung_wert` (grenze max, alt 25, neu 30, alle) wie Zeile e, also je Konfiguration umschalten und setzen.

Stand vorher und nachher je Konfiguration nach `ForceRebuild3`: `IsSuppressed2`, `GetErrorCode2`, D1, Min/Max der Definition, Lage
des Schlittens. Im Lauf vom 2026-11-05 las `fehler` die Methode statt des Codes (Rohdaten zeigen `bound method`), jetzt
`sw_baugruppe.fehlercode`. Ergebnis: `roh` in Standard lässt Hub überall aktiv; `roh_andere` und `handler` unterdrücken Hub in
Standard, max steht in beiden auf 30. Wegwerf-Qualität wie S19, Schutz aus `spikes.s19_baugruppe` (nur unter S19/, nie
AP68-Pruefstation, SolidWorks leer).

Aufruf (frisches SolidWorks, frei): timeout 600 ..\\..\\..\\.venv\\Scripts\\python.exe -m spikes.s19_e3_grenze

API (swki api methode): IFeature.GetDefinition(0), .ModifyDefinition(3), .IsSuppressed2(2), .GetErrorCode2(1), .Parameter(1);
  IDistanceMateFeatureData.MinimumDistance, .MaximumDistance; IModelDoc2.ForceRebuild3(1), .ShowConfiguration2(1)
"""

import json
import sys
import time
import traceback

from spikes.s19_baugruppe import (ERGEBNIS, KONFIG_OHNE, arbeit, e_kontext, lage_mm, mate, pruefe_leer, rechner, versuch)
from swki.baugruppe import sw_baugruppe
from swki.bestand import punkte_baugruppe
from swki.bestand.sw_bestand import schalte, unterdrueckt
from swki.speicher import privat_mb
from swki.verbindung import callout_leer, in_mm, mm, verbinde
from swki.verbindung import wert as primitiv

DATEI = ERGEBNIS / "s19_e3.json"


def stand(asm) -> dict:
    """Je Konfiguration nach dem Neuaufbau; die aktive steht danach wieder."""
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    aus = {"aktiv": aktiv}
    try:
        for k in asm.GetConfigurationNames:
            schalte(asm, k)
            asm.ForceRebuild3(False)
            f = mate(asm, "Hub")
            d = f.GetDefinition
            schlitten = next(c for c in asm.GetComponents(False) if c.Name2 == "Schlitten-1")
            aus[k] = {"unterdrueckt": versuch(lambda: unterdrueckt(f, k)), "fehler": versuch(lambda: sw_baugruppe.fehlercode(f)),
                      "d1": versuch(lambda: round(in_mm(f.Parameter("D1").SystemValue), 4)),
                      "min": versuch(lambda: round(in_mm(d.MinimumDistance), 4)),
                      "max": versuch(lambda: round(in_mm(d.MaximumDistance), 4)), "schlitten": lage_mm(schlitten)}
    finally:
        schalte(asm, aktiv)
    return aus


def roh(asm, konfiguration: str | None) -> dict:
    if konfiguration is not None:
        schalte(asm, konfiguration)
    f = mate(asm, "Hub")
    daten = f.GetDefinition
    daten.MaximumDistance = mm(30)
    r = f.ModifyDefinition(daten, asm, callout_leer())
    return {"aktiv": asm.ConfigurationManager.ActiveConfiguration.Name, "rueckgabe": r,
            "ohne_neuaufbau": {"unterdrueckt": versuch(lambda: unterdrueckt(mate(asm, "Hub"),
                                                                            asm.ConfigurationManager.ActiveConfiguration.Name))}}


def fall(app, name: str, tun) -> dict:
    pid = int(primitiv(app.GetProcessID))
    t0 = time.monotonic()
    with arbeit(app, f"e3/{name}") as (asm, ordner):
        aus = {"vorher": versuch(lambda: stand(asm))}
        aus["tun"] = versuch(lambda: tun(app, asm, ordner))
        aus["nachher"] = versuch(lambda: stand(asm))
    return aus | {"s": round(time.monotonic() - t0, 1), "mb": round(privat_mb(pid))}


def handler(app, asm, ordner) -> object:
    b = e_kontext(app, asm, ordner)
    p = {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}
    return punkte_baugruppe.PUNKTE["verknuepfung_wert"](b, p)


FAELLE = {"roh": lambda app, asm, ordner: roh(asm, None), "roh_andere": lambda app, asm, ordner: roh(asm, KONFIG_OHNE),
          "handler": handler}


def main() -> int:
    app = verbinde(rechner().sw_jahr)
    pruefe_leer(app)
    d = {"zeile": "e3", "start_mb": round(privat_mb(int(primitiv(app.GetProcessID)))), "faelle": {}}
    for name, tun in FAELLE.items():
        try:
            d["faelle"][name] = fall(app, name, tun)
        except Exception:
            d["faelle"][name] = {"fehler": traceback.format_exc()}
        DATEI.write_text(json.dumps(d, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
