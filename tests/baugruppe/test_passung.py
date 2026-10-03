import pytest

from swki.baugruppe.laden import _normteil, lade_quellen
from swki.baugruppe.passung import passt, passung_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

FAELLE = [
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8"}, True),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M8"}, True),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M10"}, False),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M8x1"}, False),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "stift", "groesse": 8}, False),
    ("ISO 4762 M10x50", {"typ": "bohrung", "durchmesser": 11}, True),
    ("ISO 4762 M10x50", {"typ": "bohrung", "durchmesser": 10}, False),
    ("ISO 8734 8x16", {"typ": "normbohrung", "art": "stift", "groesse": 8}, True),
    ("ISO 8734 8x16", {"typ": "normbohrung", "art": "stift", "groesse": 10}, False),
    ("ISO 8734 8x16", {"typ": "bohrung", "durchmesser": 8}, False),
    ("ISO 7089 M10", {"typ": "bohrung", "durchmesser": 10.5}, True),
    ("ISO 7089 M10", {"typ": "bohrung", "durchmesser": 10}, False),
    ("ISO 4032 M10", {"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M10"}, True),
]


@pytest.mark.parametrize(("normteil", "bohrung", "erwartet"), FAELLE)
def test_passt(normteil, bohrung, erwartet):
    quelle, befunde = _normteil("x", {"normteil": normteil})
    assert befunde == []
    assert (passt(quelle, bohrung, {}) is None) is erwartet


def test_passung_befund_im_beispiel(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M10x16"}
    quellen, _, befunde = lade_quellen(spec, schreibe(tmp_path / "A", baugruppe=spec).parent)
    assert befunde == []
    [b] = passung_befunde(spec, quellen)
    assert b["pfad"] == "verknuepfungen[4]" and "M10" in b["meldung"] and "zylinderschraube M8" in b["meldung"]
