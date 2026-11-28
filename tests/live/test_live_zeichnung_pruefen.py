"""Live: Zeichnungsprüfung Z1.4 Task 4b – Spannplatte Z und Buchse Z bauen, zeichnen, zurücklesen und prüfen
(Plan docs/superpowers/plans/2026-11-27-zeichnungsableitung-z14-pruefen.md; SolidWorks muss laufen, frisch gestartet).

Erwartet: Der Rückleser ändert nichts (SHA von Teil und Zeichnung gleich, danach sind nur die vorher offenen Dokumente
offen), `verdeckt` ist für jedes lineare Maß bestimmt, und kein harter Mangel stammt aus dem Rücklesen selbst – harte
Mängel kommen nur aus Meldungen der Übergabe (`swki zeichnen`, z. B. RAUHEIT_NUR_EINE_INSTANZ der Spannplatte Z)."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner
from swki.verbindung import verbinde

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).parents[1] / "referenz" / "zeichnung"
FAELLE = [("spannplatte_z.yaml", False), ("buchse_z.yaml", True)]


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _offen() -> list[str]:
    return sorted(str(d.GetPathName) for d in list(verbinde(lade_rechner().sw_jahr).GetDocuments or ()))


@pytest.mark.parametrize(("spec", "bestanden"), FAELLE)
def test_zeichnung_pruefen(capsys, tmp_path, spec, bestanden):
    auftrag = tmp_path / f"Z1-STUFE4-{Path(spec).stem}"
    auftrag.mkdir()
    spec_pfad = auftrag / spec
    shutil.copy2(REFERENZ / spec, spec_pfad)
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        lauf = str(bau["lauf"])
        code, z = _lauf(capsys, "zeichnen", str(spec_pfad), "--lauf", lauf)  # ungeprüft: nur zur Ansicht
        assert code == 0, z
        teil, drw = next(Path(bau["ordner"]).glob("*.SLDPRT")), Path(z["zeichnung"])
        vorher, offen = (_sha(teil), _sha(drw)), _offen()
        code, b = _lauf(capsys, "zeichnung", "pruefen", str(spec_pfad), "--lauf", lauf)
        assert code == 0, b
        assert (_sha(teil), _sha(drw)) == vorher, "der Rückleser hat Teil oder Zeichnung verändert"
        assert _offen() == offen, "der Rückleser hat Dokumente offen gelassen oder geschlossen"
        ziel = Path(spec_pfad.parent / "protokolle" / f"{spec_pfad.stem}.lauf-{lauf}.zeichnung.pruefbericht.json")
        assert json.loads(ziel.read_text(encoding="utf-8"))["bestanden"] == b["bestanden"]
        ist = b["ist"]
        assert ist["sha256_slddrw"] == vorher[1] and ist["format_"] == z["format"] and ist["massstab"] == z["massstab"]
        assert {a["rolle"] for a in ist["ansichten"] if a["rolle"]} == {a["rolle"] for a in z["ansichten"]}
        assert not ist["meldungen"], ist["meldungen"]
        laengen = [m for m in ist["masse"] if m["art"] == "laenge"]
        assert laengen and all(m["verdeckt"] is not None for m in laengen), [m["name"] for m in laengen]
        assert len(ist["masse"]) == z["masse"]["gesetzt"], (len(ist["masse"]), z["masse"])
        uebergabe = set(z["meldungen"])
        aus_dem_lesen = [m for m in b["maengel"] if m["text"] not in uebergabe
                         and next(p for p in b["pruefungen"] if p["id"] == m["pruefung"])["ok"] is False]
        assert aus_dem_lesen == [], aus_dem_lesen
        if bestanden:
            assert b["bestanden"] is True, b["maengel"]
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / auftrag.name, ignore_errors=True)
