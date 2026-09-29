import json

import pytest

from swki.auftrag import lauf_datei
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe

STANDARD = {"max_nachbesserungen": 3}


def _schreibe(spec_pfad, lauf, art, daten):
    pfad = lauf_datei(spec_pfad, lauf, art)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten), encoding="utf-8")


def _lauf(spec_pfad, n, bau="ok", code=None, pruefer=None):
    _schreibe(spec_pfad, n, "protokoll", {"status": bau, "dauer_s": 12.5})
    if code is not None:
        _schreibe(spec_pfad, n, "pruefbericht", {"bestanden": not code, "maengel": [{}] * code})
    if pruefer is not None:
        _schreibe(spec_pfad, n, "pruefer", {"bestanden": not pruefer, "maengel": [{}] * pruefer})


def test_laeufe_lesen(tmp_path):
    spec = tmp_path / "platte.yaml"
    _lauf(spec, 1, bau="fehler")
    _lauf(spec, 2, code=2, pruefer=1)
    _lauf(spec, 10, code=0, pruefer=0)
    _schreibe(tmp_path / "andere.yaml", 1, "protokoll", {"status": "ok", "dauer_s": 1})
    laeufe = lies_laeufe(spec)
    assert [x["lauf"] for x in laeufe] == [1, 2, 10]
    assert [x["offen"] for x in laeufe] == [1, 3, 0]
    assert laeufe[0]["pruefer"] == "ausstehend" and laeufe[1]["pruefer"] == "maengel"
    assert [x["bestanden"] for x in laeufe] == [False, False, True]


def test_keine_laeufe(tmp_path):
    assert lies_laeufe(tmp_path / "platte.yaml") == []
    assert empfehlung([], 4)[0] == "bauen"


def test_max_laeufe_vorrang():
    assert max_laeufe({}, STANDARD) == 4
    assert max_laeufe({}, STANDARD, anweisung=1) == 2
    assert max_laeufe({"max_nachbesserungen": 5}, STANDARD, anweisung=1) == 6


@pytest.mark.parametrize(("laeufe", "erwartet"), [
    ([dict(lauf=1, bau="ok", code_maengel=None, pruefer="ausstehend", offen=0, bestanden=False)], "pruefen"),
    ([dict(lauf=1, bau="ok", code_maengel=0, pruefer="ausstehend", offen=0, bestanden=False)], "pruefer"),
    ([dict(lauf=1, bau="ok", code_maengel=0, pruefer="bestanden", offen=0, bestanden=True)], "bestanden"),
    ([dict(lauf=1, bau="fehler", code_maengel=None, pruefer="ausstehend", offen=1, bestanden=False)], "nachbessern"),
    ([dict(lauf=1, bau="ok", code_maengel=2, pruefer="maengel", offen=3, bestanden=False),
      dict(lauf=2, bau="ok", code_maengel=2, pruefer="maengel", offen=3, bestanden=False)], "stopp_kein_fortschritt"),
    ([dict(lauf=1, bau="ok", code_maengel=3, pruefer="maengel", offen=4, bestanden=False),
      dict(lauf=2, bau="ok", code_maengel=1, pruefer="maengel", offen=2, bestanden=False)], "stopp_max"),
])
def test_empfehlung(laeufe, erwartet):
    assert empfehlung(laeufe, 2)[0] == erwartet
