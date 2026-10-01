import json

import pytest

from swki.auftrag import lauf_datei
from swki.cli import SwkiFehler
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe, pruefe_urteil

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
        _schreibe(spec_pfad, n, "pruefer", {"bestanden": not pruefer,
                                            "maengel": [{"knoten": [], "beschreibung": "x"}] * pruefer})


def test_laeufe_lesen(tmp_path):
    spec = tmp_path / "platte.yaml"
    _lauf(spec, 1, bau="fehler")
    _lauf(spec, 2, code=2, pruefer=1)
    _lauf(spec, 10, code=0, pruefer=0)
    _schreibe(tmp_path / "andere.yaml", 1, "protokoll", {"status": "ok", "dauer_s": 1})
    laeufe = lies_laeufe(spec)
    assert [x["lauf"] for x in laeufe] == [1, 2, 10]
    assert [x["offen"] for x in laeufe] == [None, 3, 0]
    assert [x["vergleichbar"] for x in laeufe] == [False, True, True]
    assert laeufe[0]["pruefer"] == "ausstehend" and laeufe[1]["pruefer"] == "maengel"
    assert [x["bestanden"] for x in laeufe] == [False, False, True]


def test_keine_laeufe(tmp_path):
    assert lies_laeufe(tmp_path / "platte.yaml") == []
    assert empfehlung([], 4)[0] == "bauen"


def test_max_laeufe_vorrang():
    assert max_laeufe({}, STANDARD) == 4
    assert max_laeufe({}, STANDARD, anweisung=1) == 2
    assert max_laeufe({"max_nachbesserungen": 5}, STANDARD, anweisung=1) == 6
    assert max_laeufe({}, STANDARD, anweisung=0) == 1


def _l(lauf, bau="ok", code=None, pruefer="ausstehend", offen=None, bestanden=False):
    vergleichbar = bau == "ok" and code is not None and pruefer != "ausstehend"
    return dict(lauf=lauf, bau=bau, code_maengel=code, pruefer=pruefer, offen=offen, bestanden=bestanden,
                vergleichbar=vergleichbar)


@pytest.mark.parametrize(("laeufe", "erwartet"), [
    ([_l(1)], "pruefen"),
    ([_l(1, code=0, offen=0)], "pruefer"),
    ([_l(1, code=0, pruefer="bestanden", offen=0, bestanden=True)], "bestanden"),
    ([_l(1, bau="fehler")], "nachbessern"),
    ([_l(1, code=2, pruefer="maengel", offen=3), _l(2, code=2, pruefer="maengel", offen=3)], "stopp_kein_fortschritt"),
    ([_l(1, code=3, pruefer="maengel", offen=4), _l(2, code=1, pruefer="maengel", offen=2)], "stopp_max"),
])
def test_empfehlung(laeufe, erwartet):
    assert empfehlung(laeufe, 2)[0] == erwartet


def test_bauabbruch_nach_gebautem_lauf_ist_kein_stillstand():
    # Lauf 2 bricht ab: kein Vergleich, nur ein Lauf verbraucht → weiter nachbessern
    laeufe = [_l(1, code=4, pruefer="maengel", offen=5), _l(2, bau="fehler")]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_gebauter_lauf_nach_bauabbruch_wird_nicht_mit_dem_abbruch_verglichen():
    # Lauf 1 bricht ab, Lauf 2 baut mit 3 Mängeln: früher 1 → 3 = „kein Fortschritt“, jetzt kein Vergleichslauf
    laeufe = [_l(1, bau="fehler"), _l(2, code=2, pruefer="maengel", offen=3)]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_vergleich_ueberspringt_bauabbrueche():
    # Lauf 1: 5, Lauf 2: Abbruch, Lauf 3: 6 → 6 gegen 5 → Stopp
    laeufe = [_l(1, code=4, pruefer="maengel", offen=5), _l(2, bau="fehler"), _l(3, code=5, pruefer="maengel", offen=6)]
    code, text = empfehlung(laeufe, 4)
    assert code == "stopp_kein_fortschritt"
    assert "Lauf 1" in text and "Lauf 3" in text


def test_ungepruefte_laeufe_zaehlen_nicht_als_vergleich():
    # Lauf 1 gebaut, aber nie vom Prüfer beurteilt → nicht vergleichbar; Lauf 2 ist der erste Vergleichslauf
    laeufe = [_l(1, code=1, offen=1), _l(2, code=2, pruefer="maengel", offen=3)]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_bauabbrueche_verbrauchen_laeufe():
    laeufe = [_l(1, bau="fehler"), _l(2, bau="fehler")]
    assert empfehlung(laeufe, 2)[0] == "stopp_max"


@pytest.mark.parametrize("urteil", [
    {"bestanden": True, "maengel": []},
    {"bestanden": False, "maengel": [{"knoten": ["f2"], "beschreibung": "Fase fehlt"}]},
])
def test_gueltiges_urteil(urteil, tmp_path):
    pruefe_urteil(urteil, tmp_path / "x.pruefer.json")


@pytest.mark.parametrize("urteil", [
    [],                                                    # kein Objekt
    {"bestanden": "ja", "maengel": []},                    # bestanden kein bool
    {"bestanden": False},                                  # maengel fehlt
    {"bestanden": False, "maengel": [{"knoten": "f2", "beschreibung": "x"}]},  # knoten keine Liste
    {"bestanden": False, "maengel": [{"knoten": []}]},     # beschreibung fehlt
])
def test_ungueltiges_urteil(urteil, tmp_path):
    with pytest.raises(SwkiFehler) as e:
        pruefe_urteil(urteil, tmp_path / "platte.lauf-1.pruefer.json")
    assert e.value.daten == {"code": "PRUEFER_URTEIL_UNGUELTIG"}
    assert "platte.lauf-1.pruefer.json" in str(e.value)


def test_lies_laeufe_meldet_ungueltiges_urteil(tmp_path):
    spec = tmp_path / "platte.yaml"
    _lauf(spec, 1, code=0)
    _schreibe(spec, 1, "pruefer", {"ok": True})
    with pytest.raises(SwkiFehler):
        lies_laeufe(spec)
