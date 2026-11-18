"""Live: Zeichnungsableitung Z1.3 Stufe 1 – Blatt und Ansichten ohne Maße für Buchse (Drehteil) und Spannplatte
(Frästeil) (Plan 2026-11-17 Task 5; SolidWorks muss laufen, frisch gestartet)."""

import hashlib
import json
import shutil
from itertools import combinations
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner, lade_standard
from swki.zeichnung.zuordnung import max_je_ansicht
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
        # Stufe 2: Maßplan vollständig gesetzt oder jede Lücke gemeldet; keine Ansicht über der Obergrenze
        masse = z["masse"]
        # Live 18.11.2026: kein Pflichtmaß verwerfen – über der Obergrenze nur mit ANSICHT_DICHT
        assert masse["gesetzt"] == masse["plan"], z["meldungen"]
        assert max(masse["je_ansicht"].values()) <= max_je_ansicht(lade_standard()) or any(
            m.startswith("ANSICHT_DICHT") for m in z["meldungen"]), masse
        assert not any(m.startswith(("MASS_NICHT_GELOESCHT", "MASS_NICHT_GESETZT")) for m in z["meldungen"]), z["meldungen"]
        # Nutzer 18.11.2026: lesbar – kein Text auf Text, keine Linie durch eine Maßzahl (Prüfung am PDF)
        assert not any(m.startswith("LESBARKEIT") for m in z["meldungen"]), z["meldungen"]
        # Schriftfeld zeigt den Dateinamen = Zeichnungsnummer (18.11.: PDF vor der Zeichnung gespeichert → „Zeichn1“)
        import pymupdf
        with pymupdf.open(z["pdf"]) as doc:
            assert Path(z["zeichnung"]).stem in doc[0].get_text(), "Zeichnungsnummer fehlt im Schriftfeld"
        if not drehteil:
            # Nutzer 18.11.2026: dichte Hauptansicht → Einzelheit der Kabelnut; keine Ansicht über der Obergrenze
            assert sorted(rollen) == ["drauf", "einzelheit", "haupt", "seite"], rollen
            assert max(masse["je_ansicht"].values()) <= max_je_ansicht(lade_standard()), masse
            assert any(m.startswith("EINZELHEIT: k1") for m in z["meldungen"]), z["meldungen"]
            # „Details werden in der Regel vergrößert, sonst braucht man kein Detail.“ (Nutzer 18.11.2026)
            f = {a["rolle"]: a["massstab"] for a in z["ansichten"]}
            blatt = int(z["massstab"].split(":")[0]) / int(z["massstab"].split(":")[1])
            assert f["einzelheit"] >= 2 * blatt - 1e-9 and f["haupt"] == blatt, (f, z["massstab"])
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
