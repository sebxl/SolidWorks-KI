import copy

import pytest
import yaml

from swki.spec.laden import SpecFehler, lade_spec, plausibel_befunde, schema_befunde

from .beispiel import GUELTIG


def _spec(**aenderungen):
    spec = copy.deepcopy(GUELTIG)
    spec.update(aenderungen)
    return spec


def test_gueltige_spec_hat_keine_befunde(tmp_path):
    assert schema_befunde(GUELTIG) == []
    assert plausibel_befunde(GUELTIG, tmp_path) == []


def test_lade_spec_aus_datei(tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    assert lade_spec(pfad)["name"] == "Platte_1"


def test_fehlende_datei(tmp_path):
    with pytest.raises(SpecFehler) as e:
        lade_spec(tmp_path / "fehlt.yaml")
    assert "fehlt" in e.value.daten["befunde"][0]["meldung"]


def test_unbekannte_art():
    assert schema_befunde(_spec(art="baugruppe"))[0]["pfad"] == "art"


def test_schema_meldet_pfad_und_grund():
    spec = _spec()
    del spec["features"][2]["radius"]
    [befund] = schema_befunde(spec)
    assert befund["pfad"] == "features[2]"
    assert "radius" in befund["meldung"]


def test_schema_meldet_unbekanntes_feld():
    spec = _spec()
    spec["features"][0]["farbe"] = "rot"
    assert any("farbe" in b["meldung"] for b in schema_befunde(spec))


def test_bohrung_braucht_tiefe_oder_durch():
    spec = _spec()
    del spec["features"][1]["durch"]
    assert schema_befunde(spec)


def test_doppelte_id(tmp_path):
    spec = _spec()
    spec["features"][1]["id"] = "f1"
    assert any("doppelt" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_verweis_auf_spaeteres_feature(tmp_path):
    spec = _spec()
    spec["features"][2]["kanten"] = [{"feature": "f4", "auswahl": "alle_kanten"}]
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[2].kanten[0].feature"


def test_pruefung_verweist_auf_unbekanntes_feature(tmp_path):
    spec = _spec()
    spec["pruefung"]["masse_pruefen"][0]["zu"]["feature"] = "f9"
    assert any("f9" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_unbekannter_parameter(tmp_path):
    spec = _spec()
    spec["features"][0]["ende"]["tiefe"] = "=T"
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[0].ende.tiefe" and "'T'" in befund["meldung"]


def test_masse_muessen_positiv_sein(tmp_path):
    spec = _spec()
    spec["features"][1]["durchmesser"] = "=B-60"
    [befund] = plausibel_befunde(spec, tmp_path)
    assert "durchmesser muss > 0" in befund["meldung"]


def test_versatz_darf_negativ_sein(tmp_path):
    spec = _spec()
    spec["features"][0]["skizze"]["ebene"] = {"versatz": {"ebene": "oben", "abstand": -5}}
    assert plausibel_befunde(spec, tmp_path) == []


def test_rotation_braucht_mittellinie(tmp_path):
    spec = _spec()
    spec["features"].append({
        "id": "f7", "typ": "rotation",
        "skizze": {"ebene": "vorne", "elemente": [{"polygon": {"punkte": [[1, 0], [2, 0], [2, 1]]}}]},
    })
    assert any("genau eine mittellinie" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_senkung_muss_groesser_sein(tmp_path):
    spec = _spec()
    spec["features"][1]["senkung"] = {"durchmesser": 8, "tiefe": 2}
    assert any("Senkungsdurchmesser" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_skript_wird_geprueft(tmp_path):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "f7.py").write_text("import os\ndef bauen(ctx):\n    pass\n", encoding="utf-8")
    spec = _spec()
    spec["features"].append({"id": "f7", "typ": "skript", "datei": "skripte/f7.py", "luecke": "Gewinde"})
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[6].datei" and "'os'" in befund["meldung"]


def test_skript_fehlt(tmp_path):
    spec = _spec()
    spec["features"].append({"id": "f7", "typ": "skript", "datei": "skripte/f7.py", "luecke": "Gewinde"})
    assert "fehlt" in plausibel_befunde(spec, tmp_path)[0]["meldung"]
