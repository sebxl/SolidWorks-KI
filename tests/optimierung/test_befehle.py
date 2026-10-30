"""swki optimiere <spec> und --uebernehmen (Spec C2 §4, §6) über die Kommandozeile."""

import json
from pathlib import Path

import pytest
import yaml

pytest.importorskip("optuna")
pytest.importorskip("build123d")

from swki.cli import main  # noqa: E402
from swki.optimierung.befehle import setze_parameter  # noqa: E402
from swki.spec.freigabe import FreigabeFehler, freigabe_eintrag, pruefe_freigabe  # noqa: E402
from swki.spec.laden import lade_spec  # noqa: E402

from .beispiel import lege_an, rampe  # noqa: E402


def _cli(capsys, *args) -> dict:
    code = main(list(args))
    return {"_code": code, **json.loads(capsys.readouterr().out)}


def _ziel_spec():
    return rampe(stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80], "schritt": 0.1},
                                 {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 1.0]}])


def test_uebernehmen_schreibt_werte_und_vorlage_baut_nichts_ohne_ok(tmp_path, capsys):
    pfad = lege_an(tmp_path / "rampe-auftrag", _ziel_spec())
    text = pfad.read_text(encoding="utf-8").replace("  H: 30\n", "  H: 30   # Höhe der Rampe\n")
    pfad.write_text(text, encoding="utf-8")
    assert _cli(capsys, "freigeben", str(pfad))["_code"] == 0
    arbeit = tmp_path / "arbeit"
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")
    assert erg["_code"] == 0 and erg["grund"] == "ZIEL", erg
    assert erg["raum_freigegeben"] is True and erg["lauf"].endswith("optimierung-1")
    ueber = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert ueber["_code"] == 0 and ueber["freigegeben"] is False and ueber["raum_freigegeben"] is True, ueber
    h = ueber["geschrieben"]["rampe.yaml"]["H"]
    assert abs(h * 10 - round(h * 10)) < 1e-9                    # auf dem Schritt 0,1
    assert "v0" in ueber["ablauf"]
    assert f"  H: {h:g}   # Höhe der Rampe" in pfad.read_text(encoding="utf-8")
    vorlage = Path(ueber["freigabe_vorlage"]).read_text(encoding="utf-8")
    assert "Freigabe" in vorlage and f"H: 30 → {h:g}" in vorlage and "v0" in vorlage
    with pytest.raises(FreigabeFehler):                           # ohne OK des Nutzers kein Bau
        pruefe_freigabe(pfad, lade_spec(pfad))
    frei = _cli(capsys, "freigeben", str(pfad), "--im-raum", "--quelle", ueber["quelle"])   # nach dem OK
    assert frei["_code"] == 0, frei
    pruefe_freigabe(pfad, lade_spec(pfad))
    assert freigabe_eintrag(pfad)["im_raum"]["quelle"].startswith(str(arbeit / "rampe-auftrag" / "optimierung-1"))


def _ziellauf(tmp_path, capsys, spec=None):
    pfad = lege_an(tmp_path / "auftrag", spec or _ziel_spec())
    arbeit = tmp_path / "arbeit"
    assert _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")["grund"] == "ZIEL"
    return pfad, arbeit


def _aendern(pfad, aendern) -> None:
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_uebernehmen_verweigert_andere_form(tmp_path, capsys):
    pfad, arbeit = _ziellauf(tmp_path, capsys)
    _aendern(pfad, lambda s: s["features"][0]["ende"].update(tiefe="=B+1"))
    vorher = pfad.read_text(encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert erg["_code"] == 1 and "FORM_GEAENDERT" in erg["fehler"]
    assert pfad.read_text(encoding="utf-8") == vorher            # verweigert: nichts geschrieben


def test_uebernehmen_prueft_jede_spec_nicht_nur_die_mit_stellschrauben(tmp_path, capsys):
    pfad, arbeit = _ziellauf(tmp_path, capsys)
    lauf = arbeit / "auftrag" / "optimierung-1"
    (lauf / "specs" / "rampe.yaml").write_text((lauf / "specs" / "rampe.yaml").read_text(encoding="utf-8")
                                               .replace("art: teil", "art: teil\neigenschaften: {Benennung: x}"),
                                               encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1")
    assert erg["_code"] == 1 and ("FORM_GEAENDERT" in erg["fehler"] or "LAUF_ANDERER_RAUM" in erg["fehler"])


def test_uebernehmen_verweigert_lauf_eines_anderen_raums(tmp_path, capsys):
    pfad, arbeit = _ziellauf(tmp_path, capsys)                   # Lauf 1 ZIEL bei Zielwert 0,95
    _aendern(pfad, lambda s: s["optimierung"]["ziel"].update(zielwert=2.0))
    vorher = pfad.read_text(encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert erg["_code"] == 1 and "LAUF_ANDERER_RAUM" in erg["fehler"], erg
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1")
    assert erg["_code"] == 1 and "LAUF_ANDERER_RAUM" in erg["fehler"], erg
    assert pfad.read_text(encoding="utf-8") == vorher


def test_uebernehmen_nimmt_den_letzten_ziel_lauf_des_aktuellen_raums(tmp_path, capsys):
    pfad, arbeit = _ziellauf(tmp_path, capsys)
    _aendern(pfad, lambda s: s["optimierung"].update(variante="anderer Bauweg"))
    assert _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")["grund"] == "ZIEL"
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen")
    assert erg["lauf"].endswith("optimierung-2")


def test_uebernehmen_verweigert_unzulaessige_und_abgewertete_probe(tmp_path, capsys):
    pfad, arbeit = _ziellauf(tmp_path, capsys)
    lauf = arbeit / "auftrag" / "optimierung-1"
    zeilen = [json.loads(z) for z in (lauf / "proben.jsonl").read_text(encoding="utf-8").splitlines()]
    nr = next(z["nr"] for z in zeilen if z["status"] == "simuliert")
    zeilen[nr]["zulaessig"] = False
    (lauf / "proben.jsonl").write_text("".join(json.dumps(z) + "\n" for z in zeilen), encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1",
               "--probe", str(nr))
    assert erg["_code"] == 1 and "PROBE_NICHT_ZULAESSIG" in erg["fehler"]
    zeilen[nr]["zulaessig"] = True
    (lauf / "proben.jsonl").write_text("".join(json.dumps(z) + "\n" for z in zeilen), encoding="utf-8")
    z = json.loads((lauf / "zustand.json").read_text(encoding="utf-8"))
    z["stufe2"][str(nr)] = {"abgewertet": True, "bestanden": False, "wert": 0.5}
    (lauf / "zustand.json").write_text(json.dumps(z), encoding="utf-8")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1",
               "--probe", str(nr))
    assert erg["_code"] == 1 and "PROBE_NICHT_ZULAESSIG" in erg["fehler"]


def test_uebernehmen_ohne_ziel_und_ohne_raumfreigabe(tmp_path, capsys):
    pfad = lege_an(tmp_path / "auftrag", rampe(ziel={"kennzahl": "min_anteil_richtig", "richtung": "max",
                                                     "zielwert": 2.0}, budget={"proben": 2}, pruefstufe2={"top_k": 0}))
    arbeit = tmp_path / "arbeit"
    assert _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--kerne", "2")["grund"] == "BUDGET"
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1")
    assert erg["_code"] == 1 and "--probe" in erg["fehler"]
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(arbeit), "--uebernehmen", "--lauf", "1",
               "--probe", "1")
    assert erg["_code"] == 0 and erg["freigegeben"] is False and erg["raum_freigegeben"] is False, erg


def test_fehler_vor_dem_start_liefert_grund_und_dateien(tmp_path, capsys):
    pfad = lege_an(tmp_path / "auftrag", aufgabe="raise ImportError('kaputt')\n")
    erg = _cli(capsys, "optimiere", str(pfad), "--arbeitsordner", str(tmp_path / "arbeit"), "--kerne", "2")
    assert erg["grund"] == "FEHLER" and "kaputt" in erg["detail"], erg
    assert Path(erg["plateau_md"]).is_file() and Path(erg["status_json"]).is_file()


def test_setze_parameter_block_und_fluss(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("art: teil\nparameter:\n  T: 193.5      # Trennwand\n  TT: 2\nfeatures: []\n", encoding="utf-8")
    setze_parameter(a, "T", 180.2)
    assert a.read_text(encoding="utf-8") == "art: teil\nparameter:\n  T: 180.2      # Trennwand\n  TT: 2\nfeatures: []\n"
    b = tmp_path / "b.yaml"
    b.write_text("parameter: {L: 300, B: 100, BB: 5}  # Platte\n", encoding="utf-8")
    setze_parameter(b, "B", 92)
    assert b.read_text(encoding="utf-8") == "parameter: {L: 300, B: 92, BB: 5}  # Platte\n"


def test_setze_parameter_ueber_kommentarzeile_in_spalte_null(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("parameter:\n  A: 1\n# Abschnitt\n  T: 2\nfeatures: []\n", encoding="utf-8")
    setze_parameter(a, "T", 3)
    assert a.read_text(encoding="utf-8") == "parameter:\n  A: 1\n# Abschnitt\n  T: 3\nfeatures: []\n"
