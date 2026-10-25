"""Runner `swki optimiere` (Spec C2 §4–§7) an der Test-Rampe: jedes Ende genau einmal, Automatik, eingefrorene
Bewertung, Fortsetzen, status.json und plateau.md."""

import json

import pytest
import yaml

pytest.importorskip("optuna")
pytest.importorskip("build123d")

from swki.optimierung.auftrag import lies_auftrag  # noqa: E402
from swki.optimierung.runner import Ende, Runner  # noqa: E402
from swki.spec.laden import lade_spec  # noqa: E402

from .beispiel import AUFGABE_RAMPE, lege_an, rampe  # noqa: E402


def _runner(tmp_path, spec=None, aufgabe=AUFGABE_RAMPE, lauf="optimierung-1", **kw) -> Runner:
    pfad = lege_an(tmp_path / "auftrag", spec, aufgabe)
    a = lies_auftrag(lade_spec(pfad), pfad)
    return Runner(a, tmp_path / "arbeit" / lauf, kerne=2, **kw)


def test_ziel_mit_pruefstufe2(tmp_path):
    r = _runner(tmp_path, rampe(stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80]},
                                                {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 1.0]}]))
    s = r.starte()
    assert s["grund"] == "ZIEL", s["detail"]
    b = s["bester"]
    assert b["wert"] >= 0.95 and b["stufe2"]["bestanden"] and b["stufe2"]["belastbar"]
    assert s["proben"]["simuliert"] >= 1 and s["proben"]["gesamt"] < 40
    lauf = tmp_path / "arbeit" / "optimierung-1"
    assert json.loads((lauf / "status.json").read_text(encoding="utf-8"))["grund"] == "ZIEL"
    md = (lauf / "plateau.md").read_text(encoding="utf-8")
    assert md.startswith("# ZIEL") and "swki optimiere" in md
    zeilen = [json.loads(z) for z in (lauf / "proben.jsonl").read_text(encoding="utf-8").splitlines()]
    assert zeilen[0]["werte"] == {"H": 10.0, "v0": 0.0}            # Startpunkt zuerst
    assert (lauf / "specs" / "rampe.yaml").is_file() and (lauf / "bewertung" / "aufgabe_rampe.py").is_file()


def test_plateau_mit_automatik_und_fehlerbildern(tmp_path):
    spec = rampe(ziel={"kennzahl": "mittel_anteil_richtig", "richtung": "max", "zielwert": 0.95},
                 stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 30]},
                                 {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 0.2]}],
                 start=[{"H": 30.0, "v0": 0.2}], budget={"proben": 60}, pruefstufe2={"top_k": 1, "laeufe": 24})
    s = _runner(tmp_path, spec).starte()
    assert s["grund"] == "PLATEAU", s["detail"]
    assert [p["massnahme"] for p in s["phasen"]] == ["start", "samplerwechsel"]
    assert s["bester"]["wert"] < 0.95 and s["bester"]["fehlerbilder"]
    assert any(g["name"] == "H" and not g["erweiterbar"] for g in s["grenzanschlaege"])
    md = (tmp_path / "arbeit" / "optimierung-1" / "plateau.md").read_text(encoding="utf-8")
    assert md.startswith("# PLATEAU") and "Fehlerbilder" in md and "am Rahmen" in md and len(md) < 6000
    assert "stufe2" in s["top"][0]


def test_bereich_erweitern_bis_zum_ziel(tmp_path):
    spec = rampe(ziel={"kennzahl": "mittel_anteil_richtig", "richtung": "max", "zielwert": 0.95},
                 stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80], "bereich": [5, 30]},
                                 {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 0.01]}],
                 start=[{"H": 29.8, "v0": 0.0}], plateau={"proben": 6, "epsilon": 0.0}, budget={"proben": 80})
    s = _runner(tmp_path, spec).starte()
    assert s["grund"] == "ZIEL", (s["detail"], s["phasen"])
    assert "bereich_erweitert" in [p["massnahme"] for p in s["phasen"]]
    assert s["bester"]["werte"]["H"] > 55


def test_budget(tmp_path):
    spec = rampe(ziel={"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 2.0}, budget={"proben": 3},
                 pruefstufe2={"top_k": 0})
    s = _runner(tmp_path, spec).starte()
    assert (s["grund"], s["proben"]["gesamt"]) == ("BUDGET", 3)


def test_fehler_der_pruefaufgabe(tmp_path):
    aufgabe = AUFGABE_RAMPE.replace("    p = probe[", "    raise RuntimeError('kaputt')\n    p = probe[")
    s = _runner(tmp_path, aufgabe=aufgabe).starte()
    assert s["grund"] == "FEHLER" and "kaputt" in s["detail"]


def test_startprobe_nicht_baubar(tmp_path):
    spec = rampe(start=[{"H": 50.0, "v0": 0.0}])
    spec["features"][0]["ende"]["tiefe"] = "=B-H"
    spec["parameter"]["H"] = 30
    s = _runner(tmp_path, spec).starte()
    assert s["grund"] == "FEHLER" and "Startprobe" in s["detail"]


def test_bewertung_eingefroren(tmp_path):
    r = _runner(tmp_path)
    r.pruefe_bewertung()
    (tmp_path / "auftrag" / "aufgabe_rampe.py").write_text(AUFGABE_RAMPE + "\n# anders\n", encoding="utf-8")
    with pytest.raises(Ende) as e:
        r.pruefe_bewertung()
    assert "BEWERTUNG_GEAENDERT" in e.value.detail


def test_fortsetzen(tmp_path):
    spec = rampe(ziel={"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 2.0}, budget={"proben": 3},
                 pruefstufe2={"top_k": 0})
    assert _runner(tmp_path, spec).starte()["proben"]["gesamt"] == 3
    pfad = tmp_path / "auftrag" / "rampe.yaml"
    roh = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    roh["optimierung"]["budget"] = {"proben": 5}               # Budget ist Bauweg der Schleife, nicht Bewertung
    pfad.write_text(yaml.safe_dump(roh, allow_unicode=True), encoding="utf-8")
    r = Runner(lies_auftrag(lade_spec(pfad), pfad), tmp_path / "arbeit" / "optimierung-1", kerne=2, fortsetzen=True)
    s = r.starte()
    assert (s["grund"], s["proben"]["gesamt"]) == ("BUDGET", 5)
    nr = [json.loads(z)["nr"] for z in (tmp_path / "arbeit" / "optimierung-1" / "proben.jsonl").read_text().splitlines()]
    assert nr == [0, 1, 2, 3, 4]
    (tmp_path / "auftrag" / "aufgabe_rampe.py").write_text("# anders\n" + AUFGABE_RAMPE, encoding="utf-8")
    with pytest.raises(Ende):
        Runner(lies_auftrag(lade_spec(pfad), pfad), tmp_path / "arbeit" / "optimierung-1", kerne=2, fortsetzen=True)
