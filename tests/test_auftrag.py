from pathlib import Path

from swki.auftrag import (
    auftrag_name, dateiname, lauf_belegt, lauf_datei, lauf_ordner, laeufe, naechster_lauf, protokoll_ordner,
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


def test_lauf_belegt(tmp_path):
    r = _rechner(tmp_path)
    spec = tmp_path / "auftraege" / "A" / "platte.yaml"
    assert not lauf_belegt(r, "A", spec, 1)
    lauf_ordner(r, "A", 1).mkdir(parents=True)
    assert lauf_belegt(r, "A", spec, 1)
    datei = lauf_datei(spec, 2, "protokoll")
    datei.parent.mkdir(parents=True)
    datei.write_text("{}", encoding="utf-8")
    assert lauf_belegt(r, "A", spec, 2)


def test_lauf_belegt_durch_pruefdatei_ohne_protokoll(tmp_path):
    r = _rechner(tmp_path)
    spec = tmp_path / "auftraege" / "A" / "platte.yaml"
    for art in ("pruefbericht", "pruefer"):
        datei = lauf_datei(spec, 3, art)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text("{}", encoding="utf-8")
    assert lauf_belegt(r, "A", spec, 3)
    assert not lauf_belegt(r, "A", spec, 1)
    # Dateien einer anderen Spezifikation im selben Ordner belegen den Lauf nicht
    fremd = lauf_datei(spec.with_name("andere.yaml"), 4, "protokoll")
    fremd.write_text("{}", encoding="utf-8")
    assert not lauf_belegt(r, "A", spec, 4)


def test_naechster_lauf_beruecksichtigt_protokolle(tmp_path):
    """Arbeitsordner aufgeräumt, Protokolle im (versionierten) Auftragsordner noch da: Lauf 1 ist nicht frei."""
    r = _rechner(tmp_path)
    spec = tmp_path / "auftraege" / "A" / "platte.yaml"
    for n, art in ((1, "protokoll"), (1, "pruefbericht"), (1, "pruefer"), (2, "pruefbericht")):
        datei = lauf_datei(spec, n, art)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text("{}", encoding="utf-8")
    assert laeufe(r, "A") == []
    assert naechster_lauf(r, "A", spec) == 3
    lauf_ordner(r, "A", 5).mkdir(parents=True)
    assert naechster_lauf(r, "A", spec) == 6
