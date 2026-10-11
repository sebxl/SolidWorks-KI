"""STEP lesen und Merkmalsbericht (ohne SolidWorks)."""

from pathlib import Path

import pytest

from swki.pruefung.merkmale import als_text, merkmale, merkmale_aus_datei
from swki.pruefung.step import StepFehler, lies_eintraege, lies_modell, lies_step

DATEN = Path(__file__).parent / "daten"
PLATTE = DATEN / "platte_merkmale.step"                                    # CadQuery
MOTOR = Path(__file__).parents[1] / "referenz/motorhalter/muster/gm42-10.step"  # SolidWorks 2025


def test_eintraege_einfach_zusammengesetzt_und_zeichenkette_mit_semikolon():
    text = ("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n#1 = CARTESIAN_POINT('a;b', (1.,-2.5E1,.5));\n"
            "#2 =( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );\n"
            "#3 = MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4), #2);\nENDSEC;\nEND-ISO-10303-21;\n")
    e = lies_eintraege(text)
    assert e[1] == ("CARTESIAN_POINT", ("a;b", (1.0, -25.0, 0.5)))
    assert e[2][1]["SI_UNIT"] == ("MILLI", "METRE")
    assert e[3][1][0].name == "LENGTH_MEASURE" and e[3][1][0].args == (25.4,)
    with pytest.raises(StepFehler):
        lies_eintraege("ISO-10303-21;")


def test_platte_flaechen_und_koerper():
    modell = lies_step(PLATTE)
    assert modell.koerper == 1 and modell.einheit_mm == 1.0 and len(modell.flaechen) == 45


def test_meter_werden_mm():
    text = PLATTE.read_text(encoding="utf-8").replace("SI_UNIT(.MILLI.,.METRE.)", "SI_UNIT($,.METRE.)")
    m = merkmale(lies_modell(text))
    assert m["huellquader"]["kanten"] == [100000.0, 25000.0, 60000.0]


def test_platte_merkmale():
    m = merkmale_aus_datei(PLATTE)
    assert m["huellquader"] == {"min": [-50.0, -5.0, -30.0], "max": [50.0, 20.0, 30.0], "kanten": [100.0, 25.0, 60.0]}
    senk = [b for b in m["bohrungen"] if b["durch"]]
    assert len(senk) == 4 and all(b["achse"] == "Y" for b in senk)
    assert sorted((b["mitte"]["X"], b["mitte"]["Z"]) for b in senk) == [(-40, -20), (-40, 20), (40, -20), (40, 20)]
    assert [(t["d"], t["s0"], t["s1"]) for t in senk[0]["abschnitte"]] == [(6.6, 0.0, 13.6), (11.0, 13.6, 20.0)]
    seite = next(b for b in m["bohrungen"] if b["achse"] == "X")
    assert seite["enden"] == {"-": "boden", "+": "offen"} and seite["mitte"] == {"Y": 10.0, "Z": 0.0}
    gewinde = next(b for b in m["bohrungen"] if b["achse"] == "Z")
    assert gewinde["enden"] == {"-": "offen", "+": "spitze"} and gewinde["abschnitte"][1]["winkel"] == 118.0
    assert m["zapfen"] == [{"achse": "Y", "d": 16.0, "mitte": {"X": 0.0, "Z": 0.0}, "s0": -5.0, "s1": 0.0}]
    radien = sorted({(r["r"], r["art"]) for r in m["rundungen"]})
    assert radien == [(2.0, "konvex"), (4.0, "konkav")]   # Außenecken, Taschenecken
    assert [e["hoehe"] for e in m["ebenen"]["+Y"]] == [20.0, 13.6, 12.0]   # Deckfläche, Senkungsgrund, Taschenboden
    assert {s["winkel"] for s in m["schraege"]} == {45.0}


def test_motor_aus_solidworks():
    """SolidWorks teilt volle Zylinder in zwei Hälften – sie werden wieder zusammengefasst."""
    m = merkmale_aus_datei(MOTOR)
    assert m["koerper"] == 2 and m["huellquader"]["kanten"] == [60.0, 85.0, 60.0]
    gewinde = [b for b in m["bohrungen"] if b["abschnitte"][0]["d"] == 4.2]
    assert len(gewinde) == 4 and all(b["enden"] == {"-": "offen", "+": "spitze"} for b in gewinde)
    assert sorted(z["d"] for z in m["zapfen"]) == [10.0, 40.0, 56.0]


def test_text_kompakt():
    text = als_text(merkmale_aus_datei(PLATTE))
    assert "Bohrung 4× durch: Ø6,6 Y 0…13,6 + Ø11 Y 13,6…20" in text
    assert "Bohrung 1× blind von +X, Grund boden, Tiefe 12: Ø5 X 38…50  bei (Y 10 | Z 0)" in text
    assert "Zapfen Ø16 Achse Y -5…0 bei (X 0 | Z 0)" in text
    assert len(text.splitlines()) < 30
