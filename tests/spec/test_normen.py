import pytest

from swki.spec.normen import ARTEN, groesse_text, lade_tabelle, norm_von, normmasse, verfuegbare_groessen


def test_tabelle_hat_alle_arten():
    tabelle = lade_tabelle()
    assert tabelle["bohrspitze_grad"] == 118
    assert set(tabelle["normen"]["ISO"]) == set(ARTEN)


def test_m8_kernloch_wie_s9b():
    assert normmasse("gewinde", "M8")["kernloch"] == pytest.approx(6.8)  # S9b Baustein 21: Zylinder r 3,4


@pytest.mark.parametrize(("groesse", "text"), [("M8", "M8"), (8, "8"), (8.0, "8")])
def test_groesse_text(groesse, text):
    assert groesse_text(groesse) == text


def test_groessen_der_referenz_vorhanden():
    for art, groesse in (("zylinderschraube", "M8"), ("stift", 8), ("gewinde", "M10"), ("gewinde", "M12x1.5"),
                         ("senkschraube", "M6")):
        assert normmasse(art, groesse) is not None, (art, groesse)
    assert "M8" in verfuegbare_groessen("gewinde")


def test_unbekannte_groesse_und_norm():
    assert normmasse("gewinde", "M7") is None
    assert verfuegbare_groessen("gewinde", "DIN") == []


@pytest.mark.parametrize(("feature", "standard", "norm"), [
    ({}, None, "ISO"),                              # Vorgabe aus config/standard.yaml
    ({}, {"bohrungsnorm": "DIN"}, "DIN"),
    ({"norm": "ISO"}, {"bohrungsnorm": "DIN"}, "ISO"),  # je Bohrung überschreibbar
])
def test_norm_von(feature, standard, norm):
    assert norm_von(feature, standard) == norm
