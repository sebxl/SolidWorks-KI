import pytest

from swki.baugruppe.laden import lade_quellen
from swki.baugruppe.plausibel import plausibel_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe


def _befunde(tmp_path, spec) -> list[dict]:
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return plausibel_befunde(spec, quellen)


def _meldungen(befunde) -> str:
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in befunde)


def test_beispiel_ohne_befunde(tmp_path):
    assert _befunde(tmp_path, kopie(BAUGRUPPE)) == []


@pytest.mark.parametrize("fixiert", [[], ["platte", "deckel"]])
def test_genau_eine_fixiert(tmp_path, fixiert):
    spec = kopie(BAUGRUPPE)
    for k in spec["komponenten"]:
        k.pop("fixiert", None)
        if k["id"] in fixiert:
            k["fixiert"] = True
    assert "genau eine Komponente" in _meldungen(_befunde(tmp_path, spec))


def test_je_position_auf_extrusion(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["je_position"] = {"komponente": "deckel", "feature": "f1"}
    assert "keine normbohrung/bohrung" in _meldungen(_befunde(tmp_path, spec))


def test_normteil_nur_einbaureferenzen(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][6]["a"] = {"komponente": "stift", "feature": "f1", "flaeche": "+y"}
    assert "nur über Einbaureferenzen" in _meldungen(_befunde(tmp_path, spec))


def test_unbekannte_einbaureferenz(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][3]["a"]["referenz"] = "EINBAU_EBENE_2"   # ISO 4762 hat nur EINBAU_EBENE
    assert "keine Einbaureferenz 'EINBAU_EBENE_2'" in _meldungen(_befunde(tmp_path, spec))


def test_instanz_zu_gross(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][1]["b"]["instanz"] = 3
    assert "hat nur 2 Positionen" in _meldungen(_befunde(tmp_path, spec))


def test_ausrichtung_pflicht(tmp_path):
    spec = kopie(BAUGRUPPE)
    del spec["verknuepfungen"][0]["ausrichtung"]
    assert "ausrichtung" in _meldungen(_befunde(tmp_path, spec))


def test_wert_pflicht_und_verboten(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0]["typ"] = "abstand"          # ohne wert
    spec["verknuepfungen"][2]["wert"] = 5                 # parallel mit wert
    text = _meldungen(_befunde(tmp_path, spec))
    assert "wert ist bei abstand Pflicht" in text and "wert gilt nur bei abstand/winkel" in text


def test_instanz_je_ohne_je_komponente(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][1]["b"]["instanz"] = "je"
    assert "instanz: je nur zusammen mit" in _meldungen(_befunde(tmp_path, spec))


def test_verschiedene_je_positionen(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "mutter", "quelle": {"normteil": "ISO 4032 M8"},
                                "je_position": {"komponente": "platte", "feature": "f2"}})
    spec["verknuepfungen"].append({"id": "v8", "typ": "deckungsgleich", "a": {"komponente": "mutter", "referenz": "EINBAU_EBENE"},
                                   "b": {"komponente": "schraube", "referenz": "EINBAU_EBENE"}, "ausrichtung": "gleich"})
    assert "verschiedenem je_position" in _meldungen(_befunde(tmp_path, spec))


def test_komponente_ohne_verknuepfung(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"] = spec["verknuepfungen"][:5]   # Stift ohne Verknüpfung
    assert "stift kommt in keiner Verknüpfung vor" in _meldungen(_befunde(tmp_path, spec))


@pytest.mark.parametrize(("komponente", "gueltig"), [("schraube", False), ("schraube.3", False), ("schraube.1", True)])
def test_messpunkt_instanzen(tmp_path, komponente, gueltig):
    spec = kopie(BAUGRUPPE)
    spec["pruefung"]["masse_pruefen"][0]["zu"] = {"komponente": komponente, "referenz": "EINBAU_EBENE"}
    assert (_befunde(tmp_path, spec) == []) is gueltig


def test_freiheitsgrade_unbekannt(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["freiheitsgrade"] = {"rad": "unterbestimmt"}
    assert "freiheitsgrade" in _meldungen(_befunde(tmp_path, spec))
