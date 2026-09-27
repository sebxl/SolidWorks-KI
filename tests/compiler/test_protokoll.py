import json

import pytest

from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.protokoll import Protokoll


def _protokoll() -> Protokoll:
    return Protokoll(auftrag="A", spec="platte.yaml", lauf=1, sw_jahr=2025)


def test_knoten_ok_mit_sw_name():
    p = _protokoll()
    with p.knoten_lauf("f1", "extrusion") as k:
        k.sw_name = "f1"
    [k] = p.knoten
    assert (k.id, k.status, k.sw_name) == ("f1", "ok", "f1")
    assert k.dauer_s >= 0


def test_knoten_fehler_wird_vermerkt_und_weitergereicht():
    p = _protokoll()
    with pytest.raises(BauFehler):
        with p.knoten_lauf("f2", "bohrung"):
            raise BauFehler(REFERENZ_NICHT_GEFUNDEN, "keine Fläche +y (nächster Abstand 0.4 mm)", schritt="flaeche")
    assert p.knoten[0].status == "fehler"
    assert p.knoten[0].fehler == {
        "code": REFERENZ_NICHT_GEFUNDEN, "schritt": "flaeche", "meldung": "keine Fläche +y (nächster Abstand 0.4 mm)",
    }


def test_fremde_ausnahme_wird_protokolliert():
    p = _protokoll()
    with pytest.raises(ValueError):
        with p.knoten_lauf("f3", "fase"):
            raise ValueError("kaputt")
    assert p.knoten[0].fehler == {"code": "ValueError", "schritt": None, "meldung": "kaputt"}


def test_phasen_summieren_sich():
    p = _protokoll()
    for _ in range(2):
        with p.phase("bauen"):
            pass
    assert list(p.phasen) == ["bauen"] and p.phasen["bauen"] >= 0


def test_schreiben(tmp_path):
    p = _protokoll()
    p.uebersprungen("f9", "skript")
    ziel = tmp_path / "lauf-1" / "protokoll.json"
    p.schreibe(ziel)
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["auftrag"] == "A" and daten["knoten"][0]["status"] == "uebersprungen"
