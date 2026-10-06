import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.kaufteile.ortung import (ebene_durch_achse, kandidaten, nenn_durchmesser, orte_ebene, orte_gewinde,
                                   orte_zylinder)

Y = (0.0, 1.0, 0.0)


def _zyl(punkt, achse, radius, abstand=0.0):
    return Flaeche("zylinder", punkt, achse=achse, radius=radius, abstand=abstand)


def _ebene(punkt, normale, abstand=0.0):
    return Flaeche("ebene", punkt, normale=normale, abstand=abstand)


def test_zylinder_gleicher_achse_gilt_als_eine_flaeche():
    welle, bohrung = _zyl((0, -10, 0), Y, 5.0), _zyl((0, 2, 0), (0, -1, 0), 5.0, 0.05)
    o = orte_zylinder([welle, bohrung, _zyl((30, 0, 0), Y, 5.0, 4.0)], "EINBAU_ACHSE",
                      {"nahe": [5, -15, 0], "durchmesser": 10}, 0.1)
    assert o.flaeche is welle and o.abweichung is None and o.ist["durchmesser"] == 10.0


def test_zylinder_gegenprobe_und_fehler():
    o = orte_zylinder([_zyl((0, 0, 0), Y, 6.0)], "EINBAU_ACHSE", {"nahe": [6, 0, 0], "durchmesser": 10}, 0.1)
    assert o.abweichung == "Ø 12.0000 statt 10"
    with pytest.raises(AnkerFehler) as e:
        orte_zylinder([_zyl((0, 0, 0), Y, 6.0, 0.4)], "EINBAU_ACHSE", {"nahe": [6, 0, 0], "durchmesser": 12}, 0.1)
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN" and "nächste 0.400 mm" in str(e.value)
    with pytest.raises(AnkerFehler) as e:
        orte_zylinder([_zyl((0, 0, 0), Y, 6.0), _zyl((0, 0, 0), Y, 8.0, 0.05)], "EINBAU_ACHSE",
                      {"nahe": [6, 0, 0], "durchmesser": 12}, 0.1)
    assert e.value.code == "REFERENZ_MEHRDEUTIG"


def test_ebene_mit_normale_unter_mehreren():
    vorne, hinten = _ebene((0, 0, 0), (0, -1, 0)), _ebene((0, 0, 0), (0, 1, 0), 0.0)
    o = orte_ebene([hinten, vorne], "EINBAU_FLANSCH", {"nahe": [25, 0, 25], "normale": [0, -1, 0]}, 0.1)
    assert o.flaeche is vorne and o.abweichung is None


def test_ebene_gegenprobe_normale():
    o = orte_ebene([_ebene((0, 0, 0), Y)], "EINBAU_FLANSCH", {"nahe": [25, 0, 25], "normale": [0, -1, 0]}, 0.1)
    assert o.abweichung == "Normale [0.0, 1.0, 0.0] statt [0, -1, 0] (180.000°)"


def test_ebene_mehrdeutig():
    with pytest.raises(AnkerFehler) as e:
        orte_ebene([_ebene((0, 0, 0), Y), _ebene((0, 0.08, 0), Y, 0.08)], "E", {"nahe": [0, 0, 0], "normale": [0, 1, 0]}, 0.1)
    assert e.value.code == "REFERENZ_MEHRDEUTIG"


def test_ebene_durch_achse():
    o = ebene_durch_achse("EINBAU_DREHLAGE", (0, 0, 0), (0, 2, 0), (0, 0, 25))
    assert o.abweichung is None and o.ist["normale"] == (1.0, 0.0, 0.0) and o.ist["abstand_achse"] == 25.0
    assert ebene_durch_achse("E", (0, 0, 0), Y, (0, 7, 0.5)).abweichung.startswith("nahe liegt 0.500 mm von der Achse")


def test_gewinde_kernloch_nenn_und_falsch():
    w = {"groesse": "M5", "normale": [0, -1, 0], "positionen": [[21, 0, 21], [-21, 0, 21], [0, 0, 30]]}
    flaechen = [_zyl((21, 3, 21), Y, 2.1), _zyl((21, 3, 21), Y, 5.0), _zyl((-21, 5, 21), (0, -1, 0), 2.5),
                _zyl((0, 0, 30), Y, 3.0)]
    a, b, c = orte_gewinde(flaechen, "flansch", w, 0.1)
    assert (a.name, a.ist["modell"], a.abweichung) == ("flansch.1", "kernloch", None)
    assert b.ist["modell"] == "nenn" and c.ist["modell"] is None
    assert c.abweichung == "Ø 6.0000: weder Kernloch 4.2 noch Nenn-Ø 5 (M5)"
    with pytest.raises(AnkerFehler):
        orte_gewinde(flaechen, "flansch", {**w, "positionen": [[50, 0, 0]]}, 0.1)
    assert nenn_durchmesser("M10x1") == 10.0


def test_kandidaten_vorauswahl():
    flaechen = [_ebene((0, 0, 0), (0, -1, 0)), _ebene((0, 5, 0), (0, 1, 0)), _zyl((0, 0, 0), Y, 5.0),
                _zyl((0, 0, 0), Y, 8.0)]
    assert kandidaten(flaechen, "ebene", (25, 0.05, 25), 0.1) == [flaechen[0]]
    assert kandidaten(flaechen, "zylinder", (0, 40, 5.05), 0.1) == [flaechen[2]]
