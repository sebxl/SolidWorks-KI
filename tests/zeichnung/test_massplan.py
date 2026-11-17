"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 1–2): Maßplan aus Maßprotokoll und Drehprofil."""

import json
from pathlib import Path

import yaml

from swki.zeichnung.massplan import Mass, massplan, massplan_drehteil, massplan_fraesteil

DATEN = Path(__file__).parent / "daten"
REF = Path(__file__).parents[1] / "referenz"


def _spannplatte():
    spec = yaml.safe_load((REF / "stil" / "spannplatte.yaml").read_text(encoding="utf-8"))
    protokoll = json.loads((DATEN / "spannplatte.protokoll.json").read_text(encoding="utf-8"))
    return spec, protokoll


def _nach_name(plan):
    return {m.name: m for m in plan}


def test_fraesteil_anforderungsmasse():
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    erwartet = {"D1@f1_skizze": 200, "D2@f1_skizze": 120, "D1@f1": 20, "D3@t1_skizze": 20, "D1@t1": 12, "D1@r1": 4,
                "D1@g1_positionen": 40, "D2@g1_positionen": 20, "D3@m1": 30, "D1@st_positionen": 150,
                "D2@st_positionen": 20}
    for name, wert in erwartet.items():
        assert plan[name].wert == wert and plan[name].quelle == "modell", name
    assert plan["D3@t1_skizze"].art == "lage" and plan["D1@f1_skizze"].art == "laenge" and plan["D1@r1"].art == "radius"
    assert plan["D3@t1_skizze"].merkmal == "t1" and plan["D1@g1_positionen"].merkmal == "g1"


def test_fraesteil_ohne_hilfs_und_fasenmasse():
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    assert "D1@Ebene1" not in plan and "D1@Ebene2" not in plan and "D1@st_fase" not in plan


def test_ids_eindeutig():
    plan = massplan_fraesteil(*_spannplatte())
    assert len({m.id for m in plan}) == len(plan)


def test_konstruktion_und_mittellinie_weg():
    protokoll = {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "konstruktion", "pfad": "features[0].x", "wert": 5, "bezug": None},
        {"name": "D2@f1_skizze", "art": "lage", "pfad": "features[0].skizze.elemente[1].mittellinie.von[1]", "wert": 5,
         "bezug": "ursprung"},
        {"name": "D3@f1_skizze", "art": "groesse", "pfad": "features[0].skizze.elemente[0].rechteck.breite", "wert": 9,
         "bezug": None}]}]}
    assert [m.name for m in massplan_fraesteil({"features": []}, protokoll)] == ["D3@f1_skizze"]


def _buchse():
    return yaml.safe_load((REF / "buchse" / "buchse.yaml").read_text(encoding="utf-8"))


def test_drehteil_durchmesser_je_einmal():
    plan = massplan_drehteil(_buchse())
    d = sorted(m.wert for m in plan if m.art == "durchmesser")
    assert d == [20, 30, 32, 50]
    assert all(m.quelle == "neu" and m.geometrie for m in plan if m.art == "durchmesser")


def test_drehteil_laengen_von_einem_bezug():
    plan = massplan_drehteil(_buchse())
    laengen = [m for m in plan if m.art == "laenge"]
    assert sorted(m.wert for m in laengen) == [8, 40, 43, 60]
    assert {m.geometrie["von"] for m in laengen} == {0}  # Bundanlage, keine Kette


def test_drehteil_ohne_skizzenmasse():
    plan = massplan(_buchse(), {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "lage", "pfad": "features[0].skizze.elemente[0].polygon.punkte[0][0]",
         "wert": 10, "bezug": "ursprung"}]}, {"id": "f2", "masse": [
        {"name": "D1@f2", "art": "abstand", "pfad": "features[1].abstand", "wert": 1, "bezug": None}]}]})
    namen = {m.name for m in plan if m.quelle == "modell"}
    assert namen == {"D1@f2"} and next(m for m in plan if m.name == "D1@f2").art == "fase"


def test_mass_ist_wertobjekt():
    m = Mass("x", "neu", "laenge", 5.0, "f1")
    assert m.name is None and m.geometrie is None
