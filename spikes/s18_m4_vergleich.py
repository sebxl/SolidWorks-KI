"""S18 M4: Lauf-für-Lauf-Vergleich Spec-Geometrie gegen Handmodell (Rohdaten der Sortierschritt-Studie).

Zuordnung über (seed, kerbe) der Startlage D1. Ausgabe je Fall: Anteil richtig mit 95-%-Wilson-Bereich (gültige Läufe,
Energieprüfung wie sim.py), Übereinstimmung des Einzelausgangs, Unterschied des freien Landepunkts y_frei und der
Zeit bis zum Ende der Rutsche.

Aufruf: .venv-sim\\Scripts\\python.exe -m spikes.s18_m4_vergleich <spec.json> <hand.json> [<spec.json> <hand.json> …]
"""

import json
import math
import sys
from pathlib import Path

SPRUNG_MAX = 0.02


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * (m - h), 2), round(100 * (m + h), 2)]


def anteil(res: list, was: str = "richtig") -> dict:
    ok = [r for r in res if r["sprung"] <= SPRUNG_MAX]
    k = sum(r["ergebnis"] == was for r in ok)
    return dict(prozent=round(100 * k / max(1, len(ok)), 2), bereich=wilson(k, len(ok)), n=len(ok), n_alle=len(res))


def median(x):
    x = sorted(x)
    return None if not x else x[len(x) // 2]


def vergleiche(spec_pfad: Path, hand_pfad: Path) -> dict:
    s = json.loads(spec_pfad.read_text(encoding="utf-8"))
    spec = s["laeufe"] if isinstance(s, dict) else s
    hand = json.loads(hand_pfad.read_text(encoding="utf-8"))
    hs = {(r["seed"], r["kerbe"]): r for r in hand}
    paare = [(r, hs[(r["seed"], r["kerbe"])]) for r in spec if (r["seed"], r["kerbe"]) in hs]
    gleich = sum(a["ergebnis"] == b["ergebnis"] for a, b in paare)
    dy = [abs(a["y_frei"] - b["y_frei"]) for a, b in paare if a.get("y_frei") is not None and b.get("y_frei") is not None]
    dt = [abs(a["t_ende"] - b["t_ende"]) for a, b in paare if a.get("t_ende") and b.get("t_ende")]
    return dict(spec=anteil(spec), hand=anteil(hand), spec_falsch=anteil(spec, "falsch"), hand_falsch=anteil(hand, "falsch"),
                paare=len(paare), ausgang_gleich_prozent=round(100 * gleich / max(1, len(paare)), 2),
                y_frei_median_spec=median([a["y_frei"] for a, _ in paare if a.get("y_frei") is not None]),
                y_frei_median_hand=median([b["y_frei"] for _, b in paare if b.get("y_frei") is not None]),
                y_frei_abw_median_mm=median(dy), y_frei_abw_p95_mm=sorted(dy)[int(0.95 * len(dy))] if dy else None,
                t_ende_abw_median_ms=None if not dt else round(1000 * median(dt), 1),
                sim_s=s.get("zusammenfassung", {}).get("sim_s") if isinstance(s, dict) else None)


if __name__ == "__main__":
    a = sys.argv[1:]
    out = {}
    for sp, hp in zip(a[::2], a[1::2]):
        out[Path(sp).stem] = r = vergleiche(Path(sp), Path(hp))
        print(Path(sp).stem, json.dumps(r, ensure_ascii=False))
