import json

import pytest
import yaml

from swki.baugruppe.freigabe import freigeben_baugruppe, freigegebene_teile, pruefe_freigabe_baugruppe, teil_summen
from swki.baugruppe.laden import lade_baugruppe
from swki.cli import main
from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, pruefsumme
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def test_pruefsumme_ignoriert_verknuepfungen():
    anders = kopie(BAUGRUPPE)
    anders["verknuepfungen"][2]["ausrichtung"] = "entgegengesetzt"
    anders["verknuepfungen"].pop()
    assert pruefsumme(anders, {"a.yaml": "1"}) == pruefsumme(BAUGRUPPE, {"a.yaml": "1"})


def test_pruefsumme_erfasst_komponenten():
    anders = kopie(BAUGRUPPE)
    anders["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M8x20"}
    assert pruefsumme(anders, {}) != pruefsumme(BAUGRUPPE, {})


def test_pruefsumme_erfasst_teile():
    assert pruefsumme(BAUGRUPPE, {"platte.yaml": "1"}) != pruefsumme(BAUGRUPPE, {"platte.yaml": "2"})


def test_freigeben_schreibt_alle_specs(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    eintrag = freigeben_baugruppe(bg, zeitpunkt="2026-10-03T10:00:00")
    daten = json.loads(freigabe_pfad(bg.pfad).read_text(encoding="utf-8"))
    assert set(daten) == {"probe.yaml", "platte.yaml", "deckel.yaml"}
    assert eintrag["teile"] == {"platte.yaml": daten["platte.yaml"], "deckel.yaml": daten["deckel.yaml"]}
    assert (tmp_path / "A" / "platte.freigegeben.yaml").exists() and (tmp_path / "A" / "probe.freigegeben.yaml").exists()
    assert pruefe_freigabe_baugruppe(bg)["pruefsumme"] == pruefsumme(bg.spec, teil_summen(bg))
    assert freigegebene_teile(bg)["platte.yaml"]["name"] == "Platte"


def test_geaenderte_teil_anforderung_nennt_teil(tmp_path):
    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    platte = kopie(PLATTE)
    platte["parameter"]["L"] = 110
    (pfad.parent / "platte.yaml").write_text(yaml.safe_dump(platte, allow_unicode=True), encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_baugruppe(lade_baugruppe(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET" and "platte.yaml" in str(e.value)


def test_geaenderte_verknuepfung_bleibt_freigegeben(tmp_path):
    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["b"] = {"komponente": "platte", "feature": "f1", "flaeche": "-x"}
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    pruefe_freigabe_baugruppe(lade_baugruppe(pfad))


def test_freigeben_befehl(capsys, tmp_path):
    code = main(["freigeben", str(schreibe(tmp_path / "A"))])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0, daten
    assert set(daten["teile"]) == {"platte.yaml", "deckel.yaml"} and daten["art"] == "baugruppe"


def test_stueckliste_soll_aus_der_freigabe(tmp_path):
    """Eine nach der Freigabe zusätzlich eingetragene Senkung (Bauweg) ändert das Soll der Stückliste nicht."""
    from swki.baugruppe.bewertung import stueckliste_soll
    from swki.baugruppe.freigabe import freigegebene_quellen
    from swki.konfig import lade_standard
    from tests.baugruppe.beispiel import DECKEL, kopie

    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    deckel = kopie(DECKEL)
    deckel["features"][1]["positionen"].append([0, 20])  # dritte Senkung nach der Freigabe
    schreibe(tmp_path / "A", deckel=deckel)
    bg = lade_baugruppe(pfad)
    standard = lade_standard()
    assert stueckliste_soll(bg.spec, bg.quellen, "A", standard)["ISO4762_M8x16_8_8.sldprt"] == 3
    assert stueckliste_soll(bg.spec, freigegebene_quellen(bg), "A", standard)["ISO4762_M8x16_8_8.sldprt"] == 2
