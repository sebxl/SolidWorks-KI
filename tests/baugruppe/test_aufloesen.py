import pytest

from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import dokument_name
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

STANDARD = {"namensschema": {"datei": "{auftrag}_{name}"}}


@pytest.fixture
def bg(tmp_path):
    return lade_baugruppe(schreibe(tmp_path / "A"))


def test_instanzen(bg):
    assert [i.id for i in instanzen(bg.spec, bg.quellen)] == ["platte", "deckel", "schraube.1", "schraube.2", "stift"]
    assert basis("schraube.2") == "schraube" and basis("platte") == "platte"


def test_verknuepfungen_vervielfaeltigt(bg):
    vs = verknuepfungen(bg.spec, bg.quellen)
    assert [v.id for v in vs] == ["v1", "v2", "v3", "v4.1", "v4.2", "v5.1", "v5.2", "v6", "v7"]
    v = next(v for v in vs if v.id == "v4.2")
    assert v.vorlage == "v4" and v.a["komponente"] == "schraube.2"
    assert v.b == {"komponente": "deckel", "feature": "f2", "instanz": 2, "flaeche": "+y"}


def test_drehung_sperren_vorgabe(bg):
    sperren = {v.id: v.drehung_sperren for v in verknuepfungen(bg.spec, bg.quellen)}
    assert sperren["v5.1"] and sperren["v7"]          # konzentrisch mit Normteil
    assert not sperren["v2"] and not sperren["v1"]    # zwei Eigenteile bzw. nicht konzentrisch
    spec = kopie(bg.spec)
    spec["verknuepfungen"][6]["drehung_sperren"] = False
    assert not {v.id: v.drehung_sperren for v in verknuepfungen(spec, bg.quellen)}["v7"]


def test_gepaarte_je_komponenten(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "scheibe", "quelle": {"normteil": "ISO 7089 M8"},
                                "je_position": {"komponente": "deckel", "feature": "f2"}})
    spec["verknuepfungen"].append({"id": "v8", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
                                   "b": {"komponente": "scheibe", "referenz": "EINBAU_EBENE"}, "ausrichtung": "gleich"})
    bg = lade_baugruppe(schreibe(tmp_path / "A", baugruppe=spec))
    v8 = [v for v in verknuepfungen(bg.spec, bg.quellen) if v.vorlage == "v8"]
    assert [(v.id, v.a["komponente"], v.b["komponente"]) for v in v8] == [
        ("v8.1", "schraube.1", "scheibe.1"), ("v8.2", "schraube.2", "scheibe.2")]


def test_dokument_name(bg):
    assert dokument_name(bg.quellen["platte"], "A", STANDARD) == "A_Platte.sldprt"
    assert dokument_name(bg.quellen["schraube"], "A", STANDARD) == "ISO4762_M8x16_8_8.sldprt"
