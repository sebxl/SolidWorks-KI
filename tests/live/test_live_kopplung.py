"""Live: Getriebeprobe (Spec 4b §10) – Zahnstangen- und Zahnradverknüpfung bauen (Zahnphase, Kopplung) und prüfen
(Eingriff, Sollweg, gekoppelte Freiheitsgrade, Bilder). SolidWorks muss laufen, frisch gestartet."""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-GETRIEBE"
PROBE = Path(__file__).resolve().parent / "getriebeprobe"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def probe(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    for quelle in [*PROBE.glob("*.yaml"), *(REFERENZ / n for n in ("zahnstange.yaml", "lagerbock.yaml",
                                                                    "ritzelwelle.yaml", "antriebswelle.yaml"))]:
        shutil.copy2(quelle, ordner / quelle.name)
    yield ordner / "getriebeprobe.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, spec: Path) -> dict:
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec))
    assert code == 0, bau
    return bau


def test_getriebeprobe_bauen(capsys, probe):
    bau = _baue(capsys, probe)
    knoten = {k["id"]: k["status"] for k in bau["knoten"]}
    assert [k for k in knoten if k.startswith("zahnphase:")] == ["zahnphase:k1", "zahnphase:k2"]
    assert all(knoten[k] == "ok" for k in ("zahnphase:k1", "k1", "zahnphase:k2", "k2", "grundstellung:Hub")), knoten
