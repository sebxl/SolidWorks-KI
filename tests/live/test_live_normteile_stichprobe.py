"""Live-Stichprobe (Spec 3a §12): 20 zufällige abgeglichene Normteile plus je eines für jede nicht vertretene Norm
bestehen die Selbstprüfung und werden abgelegt (Bibliothek in tmp_path; fester Seed, damit Wiederholungen dieselben
Teile bauen)."""

import random
import shutil
from dataclasses import replace

import pytest

from swki.konfig import lade_rechner
from swki.normteile import befehle
from swki.normteile.tabelle import lade_normtabelle, normen

pytestmark = pytest.mark.sw


def _stichprobe(anzahl: int = 20, seed: int = 3) -> list[tuple[str, str, str]]:
    alle = []
    for name in normen():
        t = lade_normtabelle(name)
        for g, z in t["groessen"].items():
            if z["status"] != "abgeglichen":
                continue
            for laenge in z.get("laengen") or [None]:
                for v in t["varianten"]:
                    alle.append((t["norm"], g if laenge is None else f"{g}x{laenge:g}", v))
    zufall = random.Random(seed)
    stichprobe = zufall.sample(alle, anzahl)
    vertreten = {norm for norm, _, _ in stichprobe}
    for name in sorted(normen()):
        norm = lade_normtabelle(name)["norm"]
        if norm not in vertreten:
            stichprobe.append(zufall.choice([teil for teil in alle if teil[0] == norm]))
    return stichprobe


@pytest.mark.parametrize(("norm", "groesse", "variante"), _stichprobe())
def test_stichprobe(norm, groesse, variante, tmp_path, monkeypatch):
    r = replace(lade_rechner(), normteilbibliothek=tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    ergebnis = befehle.hole(norm, groesse, variante)
    try:
        assert ergebnis["gebaut"] is True and ergebnis["pruefung"]["bestanden"] is True
    finally:
        shutil.rmtree(ergebnis["lauf"], ignore_errors=True)
