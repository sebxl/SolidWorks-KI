from swki.kaufteile.diagnose import uebersicht


def _zyl(punkt, achse, radius, auf, flaeche):
    return {"art": "zylinder", "punkt": punkt, "achse": achse, "radius": radius, "auf": auf, "flaeche_mm2": flaeche}


def _ebene(punkt, normale, auf, flaeche):
    return {"art": "ebene", "punkt": punkt, "normale": normale, "auf": auf, "flaeche_mm2": flaeche}


def test_zylinder_gleicher_achse_zusammengefasst():
    saetze = [_zyl((0, -10, 0), (0, 1, 0), 5.0, (5, -10, 0), 200.0),
              _zyl((0, 3, 0), (0, -1, 0), 5.0, (0, 3, 5), 300.0),   # gleiche Achse, Gegenrichtung
              _zyl((21.2, 0, 21.2), (0, 1, 0), 2.1, (23.3, 5, 21.2), 50.0)]
    u = uebersicht(saetze)
    assert u["zylinder_gesamt"] == 2
    welle = u["zylinder"][0]
    assert welle == {"durchmesser": 10.0, "achspunkt": [0.0, 0.0, 0.0], "richtung": [0.0, 1.0, 0.0],
                     "nahe": [0.0, 3.0, 5.0], "flaechen": 2, "flaeche_mm2": 500.0}
    assert u["zylinder"][1]["durchmesser"] == 4.2


def test_ebenen_nach_groesse_und_grenze():
    saetze = [_ebene((0, 0, 0), (0, -1, 0), (25, 0, 25), 1000.0), _ebene((0, 0, 9), (0, -1, 0), (-25, 0, 25), 800.0),
              _ebene((0, -25, 0), (0, -1, 0), (0, -25, 0), 78.5), _ebene((30, 0, 0), (1, 0, 0), (30, 5, 0), 900.0)]
    u = uebersicht(saetze, grenze=2)
    assert u["ebenen_gesamt"] == 3
    assert [e["flaeche_mm2"] for e in u["ebenen"]] == [1800.0, 900.0]
    assert u["ebenen"][0] == {"normale": [0.0, -1.0, 0.0], "abstand": 0.0, "nahe": [25.0, 0.0, 25.0], "flaechen": 2,
                              "flaeche_mm2": 1800.0}
