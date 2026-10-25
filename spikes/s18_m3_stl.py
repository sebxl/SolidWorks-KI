"""S18 M3: STL der simulationsrelevanten Teile – aus SolidWorks (lauf-28, mit der swki-venv) und aus dem Schnellbau
(mit .venv-sim) – für den Vergleich mit werkzeuge/messstand/vergleich.py.

  sw          .venv\\Scripts\\python.exe -m spikes.s18_m3_stl sw <laufordner> <ausgabeordner>
              (SolidWorks muss frei sein; öffnet die Teile des Laufs, speichert nur STL-Kopien, Teilkoordinaten)
  schnellbau  .venv-sim\\Scripts\\python.exe -m spikes.s18_m3_stl schnellbau <auftragsordner> <ausgabeordner>
"""

import json
import sys
import time
from pathlib import Path

TEILE = {   # Teil-Spec → Datei im Lauf
    "rutsche": "Rutsche", "weichenkeil": "Weichenkeil", "schieber": "Schieber", "pruefkanal": "Pruefkanal",
    "klemmleiste": "Klemmleiste", "saphirglas": "Saphirglas", "zwischenplatte": "Zwischenplatte",
    "durchlicht_effilux": "DurchlichtEffilux", "rutschentraeger": "Rutschentraeger", "durchlichtlasche": "Durchlichtlasche",
}


def sw(lauf: Path, aus: Path) -> None:
    from werkzeuge.messstand.stl_export import exportiere
    aus.mkdir(parents=True, exist_ok=True)
    zeiten = {}
    for spec, datei in TEILE.items():
        t0 = time.perf_counter()
        exportiere(lauf / f"AP68-Pruefstation_{datei}.SLDPRT", aus / f"{spec}.stl")
        zeiten[spec] = round(time.perf_counter() - t0, 2)
        print(spec, zeiten[spec], "s", flush=True)
    (aus / "zeiten.json").write_text(json.dumps(zeiten, indent=1), encoding="utf-8")


def schnellbau(ordner: Path, aus: Path) -> None:
    from build123d import export_stl
    from spikes.s18_schnellbau import baue_teil
    aus.mkdir(parents=True, exist_ok=True)
    for spec in TEILE:
        t = baue_teil(ordner / f"{spec}.freigegeben.yaml")
        export_stl(t.solid, str(aus / f"{spec}.stl"), tolerance=0.002, angular_tolerance=0.05)
        print(spec, "ok", flush=True)


if __name__ == "__main__":
    {"sw": sw, "schnellbau": schnellbau}[sys.argv[1]](Path(sys.argv[2]), Path(sys.argv[3]))
