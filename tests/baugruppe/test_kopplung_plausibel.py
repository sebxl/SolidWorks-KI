"""Format und Plausibilität der Kopplungen (Spec 4b §5.1, §5.2), Bestimmtheit gekoppelter Komponenten."""

import copy

import pytest

from swki.baugruppe.bewertung import _erlaubt_unterbestimmt
from swki.baugruppe.plausibel import plausibel_befunde
from swki.spec.laden import schema_befunde

from .beispiel_kopplung import TEILE, quellen, spec, v


def _meldungen(s: dict, teile: dict | None = None) -> list[str]:
    return [b["meldung"] for b in plausibel_befunde(s, quellen(teile))]


def _hat(meldungen: list[str], code: str) -> bool:
    return any(m.startswith(code) for m in meldungen)


def test_beispiel_ist_gueltig():
    assert schema_befunde(spec(), "baugruppe") == []
    assert _meldungen(spec()) == []


def test_schema_kennt_kopplung_und_gekoppelt():
    s = spec()
    s["freiheitsgrade"]["ritzelwelle"] = "frei"
    assert [b["pfad"] for b in schema_befunde(s, "baugruppe")] == ["freiheitsgrade.ritzelwelle"]


def test_kopplung_art():
    s = spec()
    v(s, "k1")["b"] = {"komponente": "ritzelwelle", "feature": "z2"}
    assert _hat(_meldungen(s), "KOPPLUNG_ART")
    s = spec()
    v(s, "k2")["a"] = {"komponente": "antriebswelle", "feature": "f1"}
    assert _hat(_meldungen(s), "KOPPLUNG_ART")


def test_modul_ungleich():
    teile = copy.deepcopy(TEILE)
    teile["antriebswelle"]["parameter"]["M"] = 2.5
    assert _hat(_meldungen(spec(), teile), "MODUL_UNGLEICH")


def test_reihenfolge_seite_b_steht_noch_nicht_fest():
    s = spec()
    k1, k2 = v(s, "k1"), v(s, "k2")
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] not in ("k1", "k2")] + [k2, k1]
    meldungen = _meldungen(s)
    assert any(m.startswith("KOPPLUNG_REIHENFOLGE: ritzelwelle steht beim Anlegen noch nicht fest") for m in meldungen)


def test_reihenfolge_kopplung_vor_anderer_verknuepfung():
    s = spec()
    s2 = v(s, "s2")
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] != "s2"] + [s2]
    assert any("danach noch: s2" in m for m in _meldungen(s))


def test_reihenfolge_seite_a_nicht_gekoppelt():
    s = spec()
    s["freiheitsgrade"]["antriebswelle"] = "unterbestimmt"
    assert any(m.startswith("KOPPLUNG_REIHENFOLGE: antriebswelle wird beim Bau in Phase gedreht") for m in _meldungen(s))


def test_gekoppelt_ohne_antrieb():
    s = spec()
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] != "k2"]
    s["bewegungen"][0]["erwartet"]["endlagen"].pop()
    assert _hat(_meldungen(s), "GEKOPPELT_OHNE_ANTRIEB")


def test_endlage_fehlt():
    s = spec()
    s["bewegungen"][0]["erwartet"]["endlagen"].pop()
    assert any(m == "ENDLAGE_FEHLT: antriebswelle ist gekoppelt und braucht in Schlittenhub eine Endlage drehung"
               for m in _meldungen(s))


def test_uebersetzung_widerspruch():
    s = spec()
    s["bewegungen"][0]["erwartet"]["endlagen"][3]["drehung"]["winkel"] = "=HUB*360/(pi*40)*25/49"
    meldungen = _meldungen(s)
    assert _hat(meldungen, "UEBERSETZUNG_WIDERSPRUCH: antriebswelle dreht laut Übersetzung 315.1268°")


def test_schritte_zu_grob():
    s = spec()
    s["bewegungen"][0]["schritte"] = 3
    assert any(m.startswith("SCHRITTE_ZU_GROB") and m.endswith("mindestens 4 Schritte") for m in _meldungen(s))


def test_nur_feature_ausserhalb_einer_kopplung():
    s = spec()
    v(s, "v1")["a"] = {"komponente": "schlitten", "feature": "f1"}
    assert any(m.startswith("{komponente, feature} nur bei zahnrad/zahnstange") for m in _meldungen(s))


def test_radachse_als_referenz():
    s = spec()
    v(s, "s1")["a"] = {"komponente": "ritzelwelle", "feature": "z1", "instanz": 1, "achse": True}
    assert _meldungen(s) == []
    v(s, "s1")["a"] = {"komponente": "ritzelwelle", "feature": "z1", "instanz": 2, "achse": True}
    assert any("nur die Radachse eines Stirnrads" in m for m in _meldungen(s))


@pytest.mark.parametrize("seite", [{"komponente": "lagerbock", "feature": "f2", "instanz": 1, "achse": True},
                                   {"komponente": "schlitten", "nahe": [0, 0, 0]}])
def test_grenze_referenz(seite):
    s = spec()
    v(s, "g1")["a"] = seite
    assert _hat(_meldungen(s), "GRENZE_REFERENZ")


def test_pi_ist_kein_parametername():
    s = spec()
    s["parameter"]["pi"] = 3
    assert "pi ist die Kreiszahl und kein Parametername" in _meldungen(s)


def test_gekoppelt_darf_unterbestimmt_sein():
    assert _erlaubt_unterbestimmt(spec(), "ritzelwelle") is True
    assert _erlaubt_unterbestimmt(spec(), "lagerbock") is False
