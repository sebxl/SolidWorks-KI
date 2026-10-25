"""swki schnellbau teil / mjcf über die Kommandozeile (JSON-Ausgabe, Fehler mit Code)."""

import json
from pathlib import Path

import pytest

pytest.importorskip("build123d")
pytest.importorskip("mujoco")

from swki.cli import main  # noqa: E402

REFERENZ = Path(__file__).parents[1] / "referenz"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_teil_mit_setzen_und_stl(capsys, tmp_path):
    spec = REFERENZ / "buchse" / "buchse.yaml"
    code, erg = _lauf(capsys, "schnellbau", "teil", str(spec), "--stl", str(tmp_path / "b.stl"))
    assert code == 0 and erg["volumen_mm3"] == pytest.approx(37425.1, rel=1e-5)
    assert erg["huellquader_mm"] == pytest.approx([50, 60, 50])
    assert (tmp_path / "b.stl").stat().st_size > 1000
    code, laenger = _lauf(capsys, "schnellbau", "teil", str(spec), "--setze", "L=70")
    assert code == 0 and laenger["huellquader_mm"][1] == pytest.approx(70)


def test_teil_skript_meldet_code(capsys):
    code, erg = _lauf(capsys, "schnellbau", "teil", str(REFERENZ / "formplatte" / "formplatte_ds.yaml"))
    assert code == 1 and erg["code"] == "SCHNELLBAU_NICHT_UNTERSTUETZT" and erg["feature"] == "f10"


def test_mjcf(capsys, tmp_path):
    sim = tmp_path / "sim.yaml"
    sim.write_text("zerlegung_toleranz_mm: 0.05\n", encoding="utf-8")
    code, erg = _lauf(capsys, "schnellbau", "mjcf", str(REFERENZ / "schlitten" / "linearschlitten.yaml"), str(sim),
                      str(tmp_path / "m.xml"))
    assert code == 0, erg
    assert {g["id"]: g["typ"] for g in erg["gelenke"]} == {"g1": "schub", "s1": "dreh"}
    import mujoco
    mujoco.MjModel.from_xml_path(erg["mjcf"])
