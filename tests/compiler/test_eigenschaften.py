import pytest

from swki.compiler.eigenschaften import eigenschaften_fuer, finde_material, material_passt, materialien
from swki.compiler.fehler import MATERIAL_UNBEKANNT, BauFehler

XML = """<?xml version="1.0" encoding="UTF-16"?>
<mstns:materials xmlns:mstns="http://www.solidworks.com/sldmaterials" version="2008.03">
  <classification name="DIN Stahl (Kaltarbeitsstahl)">
    <material name="1.2312 (40CrMnMoS8-6)" matid="90"/>
    <material name="1.2379 (X153CrMoV12)" matid="91"/>
  </classification>
  <classification name="Sonstiges"><material name="1.2312" matid="1"/></classification>
</mstns:materials>
"""


def _db(tmp_path, name, text=XML):
    pfad = tmp_path / name
    pfad.write_bytes(text.encode("utf-16"))  # wie die echten *.sldmat: UTF-16 mit BOM
    return str(pfad)


def test_material_passt():
    assert material_passt("1.2312 (40CrMnMoS8-6)", "1.2312")
    assert material_passt("1.2312", "1.2312")
    assert not material_passt("1.23120", "1.2312")


def test_materialien_lesen(tmp_path):
    assert materialien(tmp_path.joinpath(_db(tmp_path, "din.sldmat"))) == [
        "1.2312 (40CrMnMoS8-6)", "1.2379 (X153CrMoV12)", "1.2312",
    ]


def test_exakter_name_gewinnt(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    assert finde_material([db], "1.2312") == (db, "1.2312")


def test_eindeutiger_praefix(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    assert finde_material([str(tmp_path / "fehlt.sldmat"), db], "1.2379") == (db, "1.2379 (X153CrMoV12)")


def test_unbekannt_und_mehrdeutig(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    with pytest.raises(BauFehler) as e:
        finde_material([db], "1.4301")
    assert e.value.code == MATERIAL_UNBEKANNT
    zweite = _db(tmp_path, "zwei.sldmat", XML.replace('name="1.2312" matid="1"', 'name="1.2379 (anders)" matid="1"'))
    with pytest.raises(BauFehler, match="mehrdeutig"):
        finde_material([zweite], "1.2379")


def test_eigenschaften_fuer():
    spec = {"material": "1.2312", "eigenschaften": {"Benennung": "Platte", "Ersteller": "Konstrukteur"}}
    assert eigenschaften_fuer(spec, "A-1") == {
        "Ersteller": "Konstrukteur", "Auftrag": "A-1", "Material": "1.2312", "Benennung": "Platte",
    }
