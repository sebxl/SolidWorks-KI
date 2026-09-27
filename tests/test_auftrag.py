from pathlib import Path

from swki.auftrag import (
    auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe, naechster_lauf, protokoll_ordner,
)
from swki.konfig import Rechner


def _rechner(tmp_path) -> Rechner:
    return Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")


def test_auftrag_name(tmp_path):
    spec = tmp_path / "auftraege" / "A-4711" / "platte.yaml"
    assert auftrag_name(spec) == "A-4711"


def test_laeufe_und_naechster(tmp_path):
    r = _rechner(tmp_path)
    assert laeufe(r, "A") == [] and naechster_lauf(r, "A") == 1
    for n in (1, 2, 10):
        lauf_ordner(r, "A", n).mkdir(parents=True)
    (r.arbeitsordner / "A" / "lauf-x").mkdir()
    (r.arbeitsordner / "A" / "notiz.txt").write_text("x")
    assert laeufe(r, "A") == [1, 2, 10]
    assert naechster_lauf(r, "A") == 11


def test_dateiname():
    standard = {"namensschema": {"datei": "{auftrag}_{name}"}}
    assert dateiname({"name": "Formplatte_DS"}, "A-4711", standard) == "A-4711_Formplatte_DS"


def test_protokoll_ordner(tmp_path):
    assert protokoll_ordner(tmp_path / "a.yaml") == tmp_path / "protokolle"


def test_lauf_datei(tmp_path):
    assert lauf_datei(tmp_path / "platte.yaml", 2, "pruefbericht") == tmp_path / "protokolle" / "platte.lauf-2.pruefbericht.json"
