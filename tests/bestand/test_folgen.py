import pytest

from swki.bestand.folgen import folgen_von, kinder_von, rechte_seite
from tests.bestand.beispiel_aufnahme import AUFNAHME, aufnahme


def test_folgen_ueber_variable_transitiv():
    p = {"typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}
    assert folgen_von(p, AUFNAHME) == ["D1@Skizze1", "D3@Skizze2"]


def test_folgen_ueber_linke_seite_einer_gleichung():
    p = {"typ": "gleichung", "gleichung": "D1@Skizze1", "alt": '"L"', "neu": '"L" * 2'}
    assert folgen_von(p, AUFNAHME) == ["D3@Skizze2"]


def test_folgen_verknuepftes_paar():
    assert folgen_von({"typ": "mass", "mass": "D1@S5"}, AUFNAHME) == ["D2@S6"]
    assert folgen_von({"typ": "mass", "mass": "D2@S6"}, AUFNAHME) == ["D1@S5"]


def test_freies_mass_hat_keine_folgen():
    assert folgen_von({"typ": "mass", "mass": "D2@Skizze4"}, AUFNAHME) == []


def test_andere_punkte_haben_keine_folgen():
    assert folgen_von({"typ": "unterdruecken", "feature": "Fase3"}, AUFNAHME) == []
    assert folgen_von({"typ": "material", "neu": "1.4301"}, AUFNAHME) == []


def test_unbekannter_start_hat_keine_folgen():
    assert folgen_von({"typ": "mass", "mass": "D9@Weg"}, AUFNAHME) == []
    assert folgen_von({"typ": "gleichung", "variable": "Z", "alt": 1, "neu": 2}, AUFNAHME) == []


def test_getriebene_nie_in_folgen():
    a = aufnahme()
    for m in a["masse"]:
        if m["name"] == "D7@Skizze9":
            m["gruppe"] = "Spalt"
    a["gleichungen"].append({"index": 3, "text": '"D7@Skizze9" = "L"', "links": "D7@Skizze9", "global": False})
    assert "D7@Skizze9" not in folgen_von({"typ": "mass", "mass": "D1@S5"}, a)
    assert "D7@Skizze9" not in folgen_von({"typ": "gleichung", "variable": "L", "alt": 100, "neu": 1}, a)


def test_folgen_ueber_variable_die_von_variable_abhaengt():
    a = aufnahme()
    a["variablen"]["M"] = 200.0
    a["gleichungen"] += [{"index": 3, "text": '"M" = "L" * 2', "links": "M", "global": True},
                         {"index": 4, "text": '"D5@Skizze5" = "M"', "links": "D5@Skizze5", "global": False}]
    erg = folgen_von({"typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}, a)
    assert erg == ["D1@Skizze1", "D3@Skizze2", "D5@Skizze5"]  # M selbst ist kein Maß


def test_zyklus_haelt_nicht_an():
    a = aufnahme()
    a["gleichungen"].append({"index": 3, "text": '"L" = "D3@Skizze2"', "links": "L", "global": False})
    assert folgen_von({"typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}, a) == ["D1@Skizze1", "D3@Skizze2"]


@pytest.mark.parametrize("text,rechts", [
    ('"D1@Skizze1" = "L" * 2', '"L" * 2'),
    ('"L"= 100', "100"),
    ('"D3@Skizze2"="D1@Skizze1"+5', '"D1@Skizze1"+5'),
    ("kein gleichheitszeichen", "kein gleichheitszeichen"),
])
def test_rechte_seite(text, rechts):
    assert rechte_seite(text) == rechts


def test_kinder_transitiv():
    assert kinder_von("Bohrung2", AUFNAHME) == ["Fase3", "Verrundung1"]
    assert kinder_von("Fase3", AUFNAHME) == ["Verrundung1"]
    assert kinder_von("Verrundung1", AUFNAHME) == []
    assert kinder_von("Unbekannt", AUFNAHME) == []


def test_kinder_zyklus_haelt_nicht_an():
    a = aufnahme()
    for f in a["features"]:
        if f["name"] == "Verrundung1":
            f["kinder"] = ["Bohrung2"]
    assert kinder_von("Bohrung2", a) == ["Fase3", "Verrundung1"]
