"""Geometrie einer Probe und Prüfstufe 0 (Spec C2 §4.1) am Schnellbau, ohne SolidWorks."""

import shutil
from pathlib import Path

import pytest
import yaml

pytest.importorskip("build123d")

from swki.optimierung.auftrag import lies_auftrag  # noqa: E402
from swki.optimierung.probe import Probenbau  # noqa: E402

from .beispiel import lege_an, rampe  # noqa: E402

REFERENZ = Path(__file__).parents[1] / "referenz"


def _bau(pfad: Path, tmp_path: Path, sim=None) -> Probenbau:
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    return Probenbau(lies_auftrag(spec, pfad), pfad.parent, tmp_path / "cache", sim)


def test_teil_probe_mit_werten_und_cache(tmp_path):
    pfad = lege_an(tmp_path / "auftrag")
    pb = _bau(pfad, tmp_path)
    g = pb.baue({"H": 20.0, "v0": 0.5})
    assert g.gueltig, g.stufe0()
    d = g.daten
    assert d["parameter"]["rampe.yaml"]["H"] == 20.0 and d["parameter"]["rampe.yaml"]["L"] == 100.0
    assert list(d["stuecke"]) == ["rampe"] and len(d["stuecke"]["rampe"]) == 1
    assert d["koerper"] == {"rampe": "welt"} and d["werte"] == {"H": 20.0, "v0": 0.5}
    pb.baue({"H": 20.0, "v0": 0.9})
    assert pb.zerlegungen == {"neu": 1, "cache": 1}


def test_ungueltige_spec_wird_in_stufe0_verworfen(tmp_path):
    spec = rampe()
    spec["features"][0]["ende"]["tiefe"] = "=B-H"          # H > B: Tiefe ≤ 0
    pb = _bau(lege_an(tmp_path / "auftrag", spec), tmp_path)
    g = pb.baue({"H": 50.0, "v0": 0.0})
    assert not g.gueltig and "tiefe muss > 0" in g.befunde[0] and g.daten is None


def test_bauraum(tmp_path):
    pb = _bau(lege_an(tmp_path / "auftrag", rampe(nebenbedingungen={"bauraum": {"min": [0, 0, 0], "max": [100, 30, 40]}})),
              tmp_path)
    assert pb.baue({"H": 25.0, "v0": 0}).gueltig
    assert "außerhalb" in pb.baue({"H": 35.0, "v0": 0}).bauraum[0]


@pytest.fixture
def schlitten(tmp_path):
    ordner = tmp_path / "schlitten"
    shutil.copytree(REFERENZ / "schlitten", ordner)
    (ordner / "aufgabe.py").write_text("", encoding="utf-8")
    pfad = ordner / "linearschlitten.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    spec["optimierung"] = {"pruefaufgabe": {"modul": "aufgabe.py"},
                           "ziel": {"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 0.9},
                           "stellschrauben": [{"name": "SB", "spec": "schlitten.yaml", "parameter": "B", "rahmen": [40, 80]},
                                              {"name": "HL", "spec": "hebel.yaml", "parameter": "L", "rahmen": [40, 300]},
                                              {"name": "HUB", "parameter": "HUB", "rahmen": [100, 300]}],
                           "szenarien": [{"name": "s", "laeufe": 2}]}
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def test_kollision_je_stellung(schlitten, tmp_path):
    pb = _bau(schlitten, tmp_path)
    start = pb.baue({"SB": 60.0, "HL": 60.0, "HUB": 220.0})
    assert start.gueltig, start.stufe0()
    assert [(g.id, g.typ) for g in start.bg.gelenke] == [("g1", "schub"), ("s1", "dreh")]
    assert [s[0] for s in pb.stellungen(start.bg)] == ["grund", "g1=220mm", "s1=90°"]
    breit = pb.baue({"SB": 70.0, "HL": 60.0, "HUB": 220.0})       # Schlitten breiter als die Lücke zwischen den Leisten
    assert {(k["stellung"], k["a"], k["b"]) for k in breit.kollisionen} == {
        ("grund", "leiste_rechts", "schlitten"), ("g1=220mm", "leiste_rechts", "schlitten")}
    assert breit.kollisionen[0]["mm3"] == pytest.approx(10 * 25 * 80)
    assert pb.baue({"SB": 60.0, "HL": 60.0, "HUB": 290.0}).gueltig   # Hub über die Grundplatte hinaus: frei


def test_ausgangsstand_ist_die_spec_nicht_die_erste_probe(schlitten, tmp_path):
    pb = _bau(schlitten, tmp_path)
    erste = pb.baue({"SB": 70.0, "HL": 60.0, "HUB": 220.0})     # erste Probe schneidet: bleibt eine Kollision
    assert not erste.gueltig and pb.grund_meldung == []
