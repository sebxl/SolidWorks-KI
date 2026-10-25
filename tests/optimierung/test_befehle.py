"""swki optimiere <spec> und --uebernehmen (Spec C2 §4, §6) über die Kommandozeile."""

import json

import pytest
import yaml

pytest.importorskip("optuna")
pytest.importorskip("build123d")

from swki.cli import main  # noqa: E402
from swki.optimierung.befehle import setze_parameter  # noqa: E402
from swki.spec.freigabe import freigabe_eintrag, pruefe_freigabe  # noqa: E402
from swki.spec.laden import lade_spec  # noqa: E402

from .beispiel import lege_an, rampe  # noqa: E402


def _cli(capsys, *args) -> dict:
    code = main(list(args))
    return {"_code": code, **json.loads(capsys.readouterr().out)}


def _ziel_spec():
    return rampe(stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80], "schritt": 0.1},
                                 {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 1.0]}])


def test_optimiere_und_uebernehmen(tmp_path, capsys):
    pfad = lege_an(tmp_path / "rampe-auftrag", _ziel_spec())
    text = pfad.read_text(encoding="utf-8").replace("  H: 30\n", "  H: 30   # Höhe der Rampe\n")
    pfad.write_text(text, encoding="utf-8")
    assert _cli(capsys, "freigeben", str(pfad))["_code"] == 0
    arbeit = tmp_path / "arbeit"
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")
    assert erg["_code"] == 0 and erg["grund"] == "ZIEL", erg
    assert erg["raum_freigegeben"] is True and erg["lauf"].endswith("optimierung-1")
    ueber = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert ueber["_code"] == 0 and ueber["freigegeben"] is True, ueber
    h = ueber["geschrieben"]["rampe.yaml"]["H"]
    assert abs(h * 10 - round(h * 10)) < 1e-9                    # auf dem Schritt 0,1
    assert "v0" in ueber["ablauf"]
    assert f"  H: {h:g}   # Höhe der Rampe" in pfad.read_text(encoding="utf-8")
    pruefe_freigabe(pfad, lade_spec(pfad))                        # gebaut werden darf ohne Rückfrage
    assert freigabe_eintrag(pfad)["im_raum"]["quelle"].startswith(str(arbeit / "rampe-auftrag" / "optimierung-1"))


def test_uebernehmen_verweigert_andere_form(tmp_path, capsys):
    pfad = lege_an(tmp_path / "auftrag", _ziel_spec())
    arbeit = tmp_path / "arbeit"
    assert _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")["grund"] == "ZIEL"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    spec["features"][0]["ende"]["tiefe"] = "=B+1"
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert erg["_code"] == 1 and "FORM_GEAENDERT" in erg["fehler"]


def test_uebernehmen_ohne_ziel(tmp_path, capsys):
    pfad = lege_an(tmp_path / "auftrag", rampe(ziel={"kennzahl": "min_anteil_richtig", "richtung": "max",
                                                     "zielwert": 2.0}, budget={"proben": 2}, pruefstufe2={"top_k": 0}))
    arbeit = tmp_path / "arbeit"
    assert _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")["grund"] == "BUDGET"
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1")
    assert erg["_code"] == 1 and "--probe" in erg["fehler"]
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1",
               "--probe", "1")
    assert erg["_code"] == 0 and erg["freigegeben"] is False and erg["code"] == "RAUM_FEHLT"


def test_setze_parameter_block_und_fluss(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("art: teil\nparameter:\n  T: 193.5      # Trennwand\n  TT: 2\nfeatures: []\n", encoding="utf-8")
    setze_parameter(a, "T", 180.2)
    assert a.read_text(encoding="utf-8") == "art: teil\nparameter:\n  T: 180.2      # Trennwand\n  TT: 2\nfeatures: []\n"
    b = tmp_path / "b.yaml"
    b.write_text("parameter: {L: 300, B: 100, BB: 5}  # Platte\n", encoding="utf-8")
    setze_parameter(b, "B", 92)
    assert b.read_text(encoding="utf-8") == "parameter: {L: 300, B: 92, BB: 5}  # Platte\n"
