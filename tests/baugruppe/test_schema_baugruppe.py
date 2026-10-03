from swki.spec.laden import schema_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie


def test_beispiel_ist_gueltig():
    assert schema_befunde(BAUGRUPPE, "baugruppe") == []


def test_teil_schema_lehnt_baugruppe_ab():
    assert schema_befunde(BAUGRUPPE)[0]["pfad"] == "art"


def test_baugruppen_schema_lehnt_teil_ab():
    assert schema_befunde(PLATTE, "baugruppe")[0]["pfad"] == "art"


def test_unbekannter_verknuepfungstyp():
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0]["typ"] = "tangential"
    assert schema_befunde(spec, "baugruppe")


def test_komponenten_id_ohne_punkt():
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][1]["id"] = "deckel.1"
    assert schema_befunde(spec, "baugruppe")


def test_instanz_je_nicht_in_messpunkten():
    spec = kopie(BAUGRUPPE)
    spec["pruefung"]["masse_pruefen"][0]["von"] = {"komponente": "deckel", "feature": "f2", "instanz": "je", "achse": True}
    assert schema_befunde(spec, "baugruppe")


def test_normteil_quelle_braucht_norm_und_groesse():
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO8734"}
    assert schema_befunde(spec, "baugruppe")
