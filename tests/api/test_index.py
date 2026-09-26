import pytest

from swki.api.chm import Seite
from swki.api.index import baue, enum, meta, methode, seit_je_member, suche
from swki.api.typbib import EnumWert, Member, Parameter


@pytest.fixture
def db(tmp_path):
    members = [
        Member("IFeatureManager", "FeatureExtrusion3", "methode", [Parameter(f"p{i}", False, False) for i in range(23)]),
        Member("IFeatureManager", "FeatureExtrusion4", "methode", [Parameter("Sd", False, False)]),
        Member("ISketch", "Name", "property_get"),
        Member("ISketch", "Name", "property_put", [Parameter("Wert", False, False)]),
    ]
    enums = [EnumWert("swEndConditions_e", "swEndCondThroughAll", 1), EnumWert("swEndConditions_e", "swEndCondBlind", 0)]
    seiten = [
        Seite("a.htm", "FeatureExtrusion3 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion3",
              "Method", 2014, "Creates an extruded feature with blind end condition."),
        Seite("b.htm", "FeatureExtrusion4 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion4",
              "Method", 2026, "Newer extrusion."),
        Seite("c.htm", "Programmieranleitung", None, None, None, None, "Allgemeiner Text über Makros."),
    ]
    pfad = tmp_path / "api.sqlite"
    stat = baue(pfad, members, enums, seiten, 2025)
    assert stat == {"member": 4, "enums": 2, "seiten": 3}
    return pfad


def test_methode(db):
    [m] = methode(db, "IFeatureManager.FeatureExtrusion3")
    assert m["anzahl_parameter"] == 23
    assert m["seit"] == 2014
    assert "extruded" in m["text"]


def test_property_get_und_put(db):
    assert {m["art"] for m in methode(db, "ISketch.Name")} == {"property_get", "property_put"}


def test_methode_unbekannt(db):
    assert methode(db, "IGibts.Nicht") == []


def test_enum_sortiert(db):
    assert enum(db, "swEndConditions_e") == [
        {"name": "swEndCondBlind", "wert": 0}, {"name": "swEndCondThroughAll", "wert": 1},
    ]


def test_suche_findet_text(db):
    treffer = suche(db, "extruded blind")
    assert treffer[0]["schluessel"] == "IFeatureManager.FeatureExtrusion3"


def test_suche_oder_rueckfall(db):
    assert suche(db, "makros gibtsnichtwort")[0]["titel"] == "Programmieranleitung"


def test_suche_sonderzeichen(db):
    suche(db, 'extrusion "blind" (AND) -')  # darf nicht werfen


def test_seit_je_member(db):
    s = seit_je_member(db)
    assert s["FeatureExtrusion3"] == 2014 and s["FeatureExtrusion4"] == 2026


def test_meta(db):
    assert meta(db)["jahr"] == "2025"


def test_baue_zweimal_auf_gleichem_pfad(tmp_path):
    """Regression: baue() muss Verbindungen schließen, sonst schlägt unlink() auf Windows fehl."""
    pfad = tmp_path / "api.sqlite"

    # Erstes Bauen
    members1 = [Member("ITest", "Test1", "methode", [])]
    enums1 = [EnumWert("swTest_e", "Wert1", 1)]
    seiten1 = [Seite("a.htm", "Test1", "ITest", "Test1", "Method", 2020, "Original")]
    stat1 = baue(pfad, members1, enums1, seiten1, 2020)
    assert stat1 == {"member": 1, "enums": 1, "seiten": 1}
    assert methode(pfad, "ITest.Test1")[0]["seit"] == 2020
    assert meta(pfad)["jahr"] == "2020"

    # Zweites Bauen auf gleichem Pfad (sollte nicht mit PermissionError fehlschlagen)
    members2 = [Member("ITest", "Test2", "methode", [])]
    enums2 = [EnumWert("swTest_e", "Wert2", 2)]
    seiten2 = [Seite("b.htm", "Test2", "ITest", "Test2", "Method", 2025, "Neu")]
    stat2 = baue(pfad, members2, enums2, seiten2, 2025)
    assert stat2 == {"member": 1, "enums": 1, "seiten": 1}
    assert methode(pfad, "ITest.Test2")[0]["seit"] == 2025
    assert methode(pfad, "ITest.Test1") == []  # Das alte sollte weg sein
    assert meta(pfad)["jahr"] == "2025"
