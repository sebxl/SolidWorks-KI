import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.kaufteile.ortung import (ebene_durch_achse, gewinde_modelle, kandidaten, kernloch_bereich, nenn_durchmesser,
                                   orte_ebene, orte_gewinde, orte_zylinder, steigung)

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


def test_gewinde_kernloch_bereich_nenn_und_falsch():
    """M5: Kernloch gilt von D1 nach ISO 724 (4,134) bis zum Bohrer der Tabelle (4,2), je ± 0,01 (Spec 3c §4.3)."""
    durchmesser = [4.134, 4.16, 4.2, 5.0, 4.12, 6.0]
    w = {"groesse": "M5", "normale": [0, -1, 0], "positionen": [[10 * i, 0, 0] for i in range(len(durchmesser))]}
    flaechen = [_zyl((10 * i, 3, 0), Y, d / 2) for i, d in enumerate(durchmesser)] + [_zyl((0, 3, 0), Y, 5.0)]
    ergebnis = orte_gewinde(flaechen, "flansch", w, 0.1)
    assert [o.ist["modell"] for o in ergebnis] == ["kernloch", "kernloch", "kernloch", "nenn", None, None]
    assert [o.ist["durchmesser"] for o in ergebnis] == durchmesser
    assert (ergebnis[0].name, ergebnis[0].abweichung) == ("flansch.1", None)
    assert ergebnis[4].abweichung == "Ø 4.1200: weder Kernloch 4.134…4.2 noch Nenn-Ø 5 (M5)"
    with pytest.raises(AnkerFehler):
        orte_gewinde(flaechen, "flansch", {**w, "positionen": [[55, 0, 0]]}, 0.1)
    assert nenn_durchmesser("M10x1") == 10.0


def test_kernloch_bereich_und_steigung():
    assert [steigung(g) for g in ("M5", "M6", "M10x1", "M12x1.5", "M3", "M2")] == [0.8, 1.0, 1.0, 1.5, 0.5, None]
    assert kernloch_bereich("M5") == (4.134, 4.2) and kernloch_bereich("M6") == (4.9175, 5.0)
    assert kernloch_bereich("M3") == (2.4588, 2.5) and kernloch_bereich("M2") == (1.6, 1.6)  # M2 ohne ISO-4762-Zeile
    assert kernloch_bereich("M8x1") == (6.9175, 7.0) and kernloch_bereich("M16") == (13.835, 14.0)


def test_gewinde_modelle_je_gruppe():
    def m(d, modell="kernloch"):
        return {"ist": {"durchmesser": d, "modell": modell}, "abweichung": None}

    gemessen = {"flansch.1": m(4.134), "flansch.2": m(4.13398), "fuss.1": m(5.0, "nenn"), "deckel.1": m(4.134),
                "deckel.2": m(4.2), "seite.1": m(4.2), "seite.2": "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche"}
    assert gewinde_modelle(gemessen) == {"flansch": {"modell": "kernloch", "durchmesser": 4.134},
                                         "fuss": {"modell": "nenn", "durchmesser": 5.0}}


def test_kandidaten_vorauswahl():
    flaechen = [_ebene((0, 0, 0), (0, -1, 0)), _ebene((0, 5, 0), (0, 1, 0)), _zyl((0, 0, 0), Y, 5.0),
                _zyl((0, 0, 0), Y, 8.0)]
    assert kandidaten(flaechen, "ebene", (25, 0.05, 25), 0.1) == [flaechen[0]]
    assert kandidaten(flaechen, "zylinder", (0, 40, 5.05), 0.1) == [flaechen[2]]
