"""Stufe 4a: Format der Bewegungen – Schema, Auflösen von Grenze und Scharnier, Prüfsumme, Soll der Grenzverknüpfung."""

import json

import pytest

from swki.aenderungen import soll_verknuepfungswerte
from swki.baugruppe.aufloesen import verknuepfungen
from swki.baugruppe.laden import lade_quellen
from swki.spec.freigabe import PRUEF_FELDER_BAUGRUPPE, _sha256, pruefsumme
from swki.spec.laden import schema_befunde
from tests.baugruppe.beispiel import BAUGRUPPE as STATISCH
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, kopie, schreibe


def _quellen(tmp_path, spec):
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return quellen


def test_schema_bewegungsprobe_gueltig():
    assert schema_befunde(kopie(BAUGRUPPE), "baugruppe") == []


@pytest.mark.parametrize("aendern", [
    lambda s: s["freiheitsgrade"].update(schieber=0),
    lambda s: s["freiheitsgrade"].update(schieber="frei"),
    lambda s: s["bewegungen"][0].update(schritte=1),
    lambda s: s["bewegungen"][0].update(von=0),
    lambda s: s["bewegungen"][0]["erwartet"]["endlagen"][0].update(drehung={"achse": [0, 1, 0], "winkel": 90}),
    lambda s: s["verknuepfungen"][2].update(typ="grenze"),
])
def test_schema_lehnt_ab(aendern):
    spec = kopie(BAUGRUPPE)
    aendern(spec)
    assert schema_befunde(spec, "baugruppe")


def test_scharnier_wird_zu_achse_und_anlage(tmp_path):
    spec = kopie(BAUGRUPPE)
    vs = verknuepfungen(spec, _quellen(tmp_path, spec))
    assert [v.id for v in vs] == ["v1", "v2", "g1", "v3", "v4", "s1", "s1.anlage", "g2"]
    v = {x.id: x for x in vs}
    assert (v["s1"].typ, v["s1"].drehung_sperren, v["s1"].ausrichtung, v["s1"].b) == (
        "konzentrisch", False, None, {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"})
    assert (v["s1.anlage"].typ, v["s1.anlage"].ausrichtung, v["s1.anlage"].vorlage) == (
        "deckungsgleich", "entgegengesetzt", "s1")
    assert v["s1.anlage"].a == {"komponente": "hebel", "feature": "f1", "flaeche": "-y"}
    assert (v["g1"].typ, v["g1"].min, v["g1"].max, v["g1"].wert, v["g1"].drehung_sperren) == (
        "grenze_abstand", 0, "=HUB", None, False)
    assert v["v4"].drehung_sperren is True  # konzentrisch mit Normteil wie bisher


def test_scharnier_ausrichtung_der_anlage_aus_der_spec(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][5]["ausrichtung"] = "gleich"
    v = {x.id: x for x in verknuepfungen(spec, _quellen(tmp_path, spec))}
    assert v["s1.anlage"].ausrichtung == "gleich" and v["s1"].ausrichtung is None


def test_pruefsumme_ohne_bewegungen_unveraendert():
    spec = kopie(STATISCH)
    kern = {f: spec.get(f) for f in PRUEF_FELDER_BAUGRUPPE}
    assert pruefsumme(spec) == _sha256(json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def test_pruefsumme_schuetzt_bewegungen():
    spec = kopie(BAUGRUPPE)
    vorher = pruefsumme(spec)
    spec["bewegungen"][0]["schritte"] = 8
    assert pruefsumme(spec) != vorher
    ohne = kopie(BAUGRUPPE)
    ohne.pop("bewegungen")
    assert pruefsumme(ohne) != vorher


def test_soll_der_grenze_ist_der_wert_in_grundstellung(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["min"] = "=HUB/4"
    assert soll_verknuepfungswerte(spec, _quellen(tmp_path, spec)) == {"g1": 25.0, "g2": 0.0}
