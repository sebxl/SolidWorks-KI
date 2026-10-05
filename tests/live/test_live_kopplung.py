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


def test_getriebeprobe_besteht_pruefung(capsys, probe):
    _baue(capsys, probe)
    code, bericht = _lauf(capsys, "pruefen", str(probe))
    assert code == 0 and bericht["maengel"] == [], json.dumps(bericht["maengel"], indent=1, ensure_ascii=False)
    p = {x["id"]: x for x in bericht["pruefungen"]}
    for pid in ("eingriff:k1", "eingriff:k2", "freiheitsgrad:zahnstange", "freiheitsgrad:ritzelwelle",
                "freiheitsgrad:antriebswelle", "sollweg:Hub:zahnstange", "sollweg:Hub:ritzelwelle",
                "sollweg:Hub:antriebswelle", "endlage:Hub:ritzelwelle", "endlage:Hub:antriebswelle", "kollision"):
        assert p[pid]["ok"] is True, p[pid]
    assert p["endlage:Hub:ritzelwelle"]["ist"]["aufsummiert"] == pytest.approx(60 * 360 / (3.141592653589793 * 40), abs=0.01)
    assert {"k1-eingriff", "k2-eingriff"} <= set(bericht["bilder"])
    assert all(Path(x).stat().st_size > 0 for x in bericht["bilder"].values())
    assert [k["kopplung"] for k in bericht["kopplungen"]] == ["k1", "k2"]
