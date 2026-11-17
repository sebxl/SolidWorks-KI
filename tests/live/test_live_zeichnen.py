"""Live: Zeichnungsableitung Z1.3 Stufe 1 – Blatt und Ansichten ohne Maße für Buchse (Drehteil) und Spannplatte
(Frästeil) (Plan 2026-11-17 Task 5; SolidWorks muss laufen, frisch gestartet)."""

import hashlib
import json
import shutil
from itertools import combinations
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner
from swki.zeichnung.blatt import MASSSTAEBE, SCHRIFTFELD_MM, zeichenfeld

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).parents[1] / "referenz"
FAELLE = [("buchse", "buchse.yaml", True), ("stil", "spannplatte.yaml", False)]


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _ueberlappt(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize(("ordner", "spec", "drehteil"), FAELLE)
def test_zeichnen(capsys, tmp_path, ordner, spec, drehteil):
    auftrag = tmp_path / f"SWKI-LIVE-ZEICHNEN-{ordner}"
    shutil.copytree(REFERENZ / ordner, auftrag)
    spec_pfad = auftrag / spec
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        teil = next(Path(bau["ordner"]).glob("*.SLDPRT"))
        sha = hashlib.sha256(teil.read_bytes()).hexdigest()
        code, z = _lauf(capsys, "zeichnen", str(spec_pfad), "--lauf", str(bau["lauf"]))  # ungeprüft: nur zur Ansicht
        assert code == 0, z
        ablage = lade_rechner().arbeitsordner / "Z1-STUFE1"  # bleibt für die Durchsicht durch den Nutzer
        ablage.mkdir(exist_ok=True)
        for schluessel in ("pdf", "png"):
            shutil.copy2(z[schluessel], ablage / Path(z[schluessel]).name)
        for schluessel in ("zeichnung", "pdf", "png"):
            assert Path(z[schluessel]).stat().st_size > 0, schluessel
        assert z["format"] in ("A4", "A3quer")
        assert tuple(int(x) for x in z["massstab"].split(":")) in MASSSTAEBE
        rollen = [a["rolle"] for a in z["ansichten"]]
        assert "haupt" in rollen
        assert any(m.startswith("LAUF_NICHT_BESTANDEN") for m in z["meldungen"])
        if drehteil:
            assert z["schnitt"] and z["schnitt"].startswith("Schnitt") and "seite" in rollen
        x0, y0, x1, y1 = zeichenfeld(z["format"])
        schrift = (x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])
        umrisse = [a["umriss_mm"] for a in z["ansichten"]]
        for u in umrisse:
            assert x0 <= u[0] and u[2] <= x1 and y0 <= u[1] and u[3] <= y1, u
            assert not _ueberlappt(u, schrift), u
        for a, b in combinations(umrisse, 2):
            assert not _ueberlappt(a, b), (a, b)
        assert hashlib.sha256(teil.read_bytes()).hexdigest() == sha
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)
