"""Live-Negativfall der Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60): zu lange Flanschschrauben ISO 4762
M5 × 16 – die Einschraublänge (16 − 4,6 = 11,4 mm) überschreitet Gewindetiefe und Bohrtiefe 10 des Kaufteil-Gewindes
(Nanotec GPLE60-2S-32). Erwartet genau die vier Mängel gewinde:flanschschraube.<i>; sonst nichts."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner
from tests.referenz.test_referenzen import REFERENZEN, bereite_vor

pytestmark = pytest.mark.sw


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_zu_lange_flanschschraube(capsys, tmp_path):
    auftrag = tmp_path / "NEG-MOTORHALTER"
    shutil.copytree(REFERENZEN / "motorhalter", auftrag)
    spec_pfad = auftrag / "motorhalter.yaml"
    spec = yaml.safe_load(spec_pfad.read_text(encoding="utf-8"))
    assert spec["komponenten"][3]["id"] == "flanschschraube"
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO 4762 M5x16"}
    spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bereite_vor("motorhalter")
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert {m["pruefung"] for m in bericht["maengel"]} == {f"gewinde:flanschschraube.{i}" for i in range(1, 5)}, \
            bericht["maengel"]
        assert all("Einschraublänge 11.40 mm größer als Gewindetiefe 10" in m["beschreibung"] for m in bericht["maengel"])
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / "NEG-MOTORHALTER", ignore_errors=True)
