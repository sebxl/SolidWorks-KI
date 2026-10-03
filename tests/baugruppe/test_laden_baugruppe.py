import pytest

from swki.baugruppe.laden import lade_baugruppe
from swki.spec.laden import SpecFehler, art_der_datei
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def _befunde(pfad) -> list[dict]:
    with pytest.raises(SpecFehler) as e:
        lade_baugruppe(pfad)
    return e.value.daten["befunde"]


def test_laedt_quellen(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    q = bg.quellen["schraube"]
    assert (q.art, q.norm, q.groesse, q.laenge, q.variante) == ("normteil", "ISO 4762", "M8", 16.0, "8.8")
    assert q.schluessel == "ISO4762_M8x16_8_8" and q.hole_groesse == "M8x16" and q.masse["p"] == 1.25
    assert {"EINBAU_ACHSE", "EINBAU_EBENE_1", "EINBAU_EBENE_2"} <= bg.quellen["stift"].referenzen
    assert list(bg.teile) == ["platte.yaml", "deckel.yaml"] and bg.quellen["platte"].datei == "platte.yaml"
    assert bg.komponente_von("deckel.yaml") == "deckel"


def test_normlaenge_ungueltig(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M8x17"}
    [b] = _befunde(schreibe(tmp_path / "A", baugruppe=spec))
    assert b["pfad"] == "komponenten.schraube.quelle" and "NORMLAENGE_UNGUELTIG" in b["meldung"]


def test_teil_datei_fehlt(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][1]["quelle"] = {"teil": "fehlt.yaml"}
    [b] = _befunde(schreibe(tmp_path / "A", baugruppe=spec))
    assert b["pfad"].startswith("deckel: ") and "fehlt" in b["meldung"]


def test_befund_in_teil_spec_mit_komponente(tmp_path):
    platte = kopie(PLATTE)
    platte["features"][1]["groesse"] = "M7"
    befunde = _befunde(schreibe(tmp_path / "A", platte=platte))
    assert any(b["pfad"] == "platte: features[1].groesse" for b in befunde)


def test_art_der_datei(tmp_path):
    pfad = schreibe(tmp_path / "A")
    assert art_der_datei(pfad) == "baugruppe"
    assert art_der_datei(pfad.parent / "platte.yaml") == "teil"
    assert art_der_datei(pfad.parent / "fehlt.yaml") is None
