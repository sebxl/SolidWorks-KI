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


NB = {
    "id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
    "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+20", 0], ["=L/2-20", 0]], "durch": True,
}
TASCHE = {
    "id": "f7", "typ": "schnitt",
    "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
               "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 10}}]},
    "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "abstand": 5},
}


def _mit_feature(*features):
    spec = _spec()
    spec["features"] = [spec["features"][0], *features]
    spec["pruefung"] = {"huellquader": ["=L", "=H", "=B"]}
    return spec


def _mit_element(element):
    spec = _spec()
    spec["features"][0]["skizze"]["elemente"] = [element]
    return spec


def test_normbohrung_gueltig(tmp_path):
    gewinde = {k: v for k, v in NB.items() if k != "durch"} | {"id": "f3", "art": "gewinde", "groesse": "M10",
                                                               "tiefe": 16, "gewindetiefe": 12}
    stift = NB | {"id": "f4", "art": "stift", "groesse": 8}
    spec = _mit_feature(NB, gewinde, stift)
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize(("art", "groesse"), [("gewinde", "M7"), ("stift", "M8")])
def test_normbohrung_groesse_nicht_in_tabelle(tmp_path, art, groesse):
    [befund] = plausibel_befunde(_mit_feature(NB | {"art": art, "groesse": groesse}), tmp_path)
    assert befund["pfad"] == "features[1].groesse"
    assert "nicht in der Maßtabelle" in befund["meldung"] and "verfügbar:" in befund["meldung"]


@pytest.mark.parametrize(("aenderung", "meldung"), [
    ({"gewindetiefe": 10}, "nur bei art: gewinde"),
    ({"art": "gewinde", "groesse": "M10", "durch": None, "tiefe": 16}, "Pflicht"),
    ({"art": "gewinde", "groesse": "M10", "durch": None, "tiefe": 16, "gewindetiefe": 20}, "nicht größer als tiefe"),
])
def test_gewindetiefe_regeln(tmp_path, aenderung, meldung):
    nb = {k: v for k, v in (NB | aenderung).items() if v is not None}
    spec = _mit_feature(nb)
    assert schema_befunde(spec) == []
    assert any(meldung in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_normbohrung_braucht_tiefe_oder_durch():
    assert schema_befunde(_mit_feature({k: v for k, v in NB.items() if k != "durch"}))


def test_runde_skizzenelemente_gueltig(tmp_path):
    spec = _spec()
    spec["features"][0]["skizze"]["elemente"] = [
        {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B", "radius": 6}},
        {"polygon": {"punkte": [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]], "radien": [0, 3, 3, 5, 3, 3]}},
        {"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": 0}},
        {"kontur": {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                                  {"linie": [0, 30]}, {"linie": [0, 0]}]}},
    ]
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize(("element", "pfad"), [
    ({"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 20, "radius": 10}}, "rechteck.radius"),
    ({"polygon": {"punkte": [[0, 0], [40, 0], [40, 10], [0, 10]], "radien": 5}}, "polygon.radien"),
])
def test_eckradius_zu_gross(tmp_path, element, pfad):
    befunde = plausibel_befunde(_mit_element(element), tmp_path)
    assert befunde and all(b["pfad"].startswith(f"features[0].skizze.elemente[0].{pfad}") for b in befunde)
    assert "halbe" in befunde[0]["meldung"]


def test_radien_passen_nicht_zur_eckenzahl(tmp_path):
    element = {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": [1, 2, 3]}}
    [befund] = plausibel_befunde(_mit_element(element), tmp_path)
    assert "3 Werte für 4 Ecken" in befund["meldung"]


def test_kontur_bogen_ungleich_weit(tmp_path):
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 31], "mitte": [40, 15]},
                                            {"linie": [0, 31]}, {"linie": [0, 0]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert befund["pfad"] == "features[0].skizze.elemente[0].kontur.segmente[1]"
    assert "ungleich weit" in befund["meldung"]


def test_kontur_nicht_geschlossen(tmp_path):
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                            {"linie": [0, 30]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert "nicht geschlossen" in befund["meldung"]


def test_langloch_winkel_bereich(tmp_path):
    spec = _mit_element({"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 8, "winkel": 0}})
    assert plausibel_befunde(spec, tmp_path) == []
    spec["features"][0]["skizze"]["elemente"][0]["langloch"]["winkel"] = 180
    [befund] = plausibel_befunde(spec, tmp_path)
    assert "[0, 180)" in befund["meldung"]


def test_ende_bis_flaeche_und_versatz_gueltig(tmp_path):
    spec = _spec()
    spec["features"] += [TASCHE, TASCHE | {"id": "f8", "ende": {"typ": "bis_flaeche",
                                                               "flaeche": {"feature": "f7", "flaeche": "+y"}}}]
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


def test_ende_versatz_braucht_abstand():
    spec = _spec()
    spec["features"].append(TASCHE | {"ende": {"typ": "versatz_von_flaeche",
                                               "flaeche": {"feature": "f1", "flaeche": "-y"}}})
    assert schema_befunde(spec)


def test_ende_flaeche_nur_auf_fruehere_features(tmp_path):
    spec = _spec()
    spec["features"].append(TASCHE | {"ende": TASCHE["ende"] | {"flaeche": {"feature": "f9", "flaeche": "-y"}}})
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[6].ende.flaeche.feature"


def test_ende_felder_passen_zum_typ(tmp_path):
    spec = _spec()
    spec["features"] += [
        TASCHE | {"ende": {"typ": "blind", "tiefe": 5, "flaeche": {"feature": "f1", "flaeche": "-y"}}},
        TASCHE | {"id": "f8", "ende": {"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "tiefe": 5}},
    ]
    meldungen = [b["meldung"] for b in plausibel_befunde(spec, tmp_path)]
    assert any("flaeche gilt nur" in m for m in meldungen)
    assert any("tiefe gilt nicht" in m for m in meldungen)


@pytest.mark.parametrize("fid", ["achse_x", "f1_skizze", "f2_senkung", "f3_positionen"])
def test_reservierte_ids(tmp_path, fid):
    spec = _spec()
    spec["features"][1] = spec["features"][1] | {"id": fid}
    spec["pruefung"]["masse_pruefen"] = []
    befunde = plausibel_befunde(spec, tmp_path)
    assert any(b["pfad"] == "features[1].id" and "reserviert" in b["meldung"] for b in befunde)


def test_id_eines_skript_zusatzfeatures_ist_reserviert(tmp_path):
    spec = _spec()
    skript = {"id": "f7", "typ": "skript", "datei": "f7.py", "luecke": "Test"}
    spec["features"] += [skript, {**spec["features"][3], "id": "f7_2"}]
    (tmp_path / "f7.py").write_text("def bauen(ctx):\n    pass\n", encoding="utf-8")
    befunde = plausibel_befunde(spec, tmp_path)
    assert any(b["pfad"] == "features[7].id" and "reserviert" in b["meldung"] for b in befunde)
    assert [b["pfad"] for b in befunde] == ["features[7].id"]  # Minimalskript ist zulässig: einziger Befund


def test_normbohrung_doppelte_position(tmp_path):
    nb = NB | {"positionen": [["=-L/2+20", 0], [-30, 0]]}  # L = 100 → beide bei u = −30
    [befund] = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert befund["pfad"] == "features[1].positionen[1]" and "doppelt" in befund["meldung"]


@pytest.mark.parametrize(("art", "groesse", "tiefe", "ok"), [
    ("zylinderschraube", "M8", 8, False),   # Senktiefe M8 laut Tabelle 8,6 mm
    ("zylinderschraube", "M8", 20, True),
    ("senkschraube", "M6", 3, False),       # Kegelhöhe M6: (13,44 − 6,6) / 2 / tan 45° = 3,42 mm
    ("senkschraube", "M6", 10, True),
])
def test_normbohrung_tiefe_gegen_senkung(tmp_path, art, groesse, tiefe, ok):
    nb = {k: v for k, v in NB.items() if k != "durch"} | {"art": art, "groesse": groesse, "tiefe": tiefe}
    befunde = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert (befunde == []) is ok
    if not ok:
        assert befunde[0]["pfad"] == "features[1].tiefe" and "Senk" in befunde[0]["meldung"]


def test_kontur_kreissektor_wird_abgelehnt(tmp_path):
    # Viertelkreis: Mittelpunkt (0, 0) ist zugleich Eckpunkt der Kontur
    kontur = {"start": [0, 0], "segmente": [{"linie": [20, 0]}, {"bogen": [0, 20], "mitte": [0, 0]}, {"linie": [0, 0]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert befund["pfad"] == "features[0].skizze.elemente[0].kontur.segmente[1]"
    assert "Konturpunkt" in befund["meldung"]


@pytest.mark.parametrize("element", [
    {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": "=X"}},
    {"kontur": {"start": [0, 0], "segmente": [{"linie": ["=X", 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                              {"linie": [0, 30]}, {"linie": [0, 0]}]}},
])
def test_ausdrucksfehler_in_rundungen_genau_ein_befund(tmp_path, element):
    [befund] = plausibel_befunde(_mit_element(element), tmp_path)
    assert "unbekannter Parameter 'X'" in befund["meldung"]


def test_ausdrucksfehler_in_gewindetiefe_genau_ein_befund(tmp_path):
    nb = {k: v for k, v in NB.items() if k != "durch"} | {"art": "gewinde", "groesse": "M10", "tiefe": 16,
                                                         "gewindetiefe": "=X"}
    [befund] = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert "unbekannter Parameter 'X'" in befund["meldung"]


@pytest.mark.parametrize("ref", [
    {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
    {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
    {"id": "EINBAU_EBENE_2", "typ": "referenz", "ebene": {"basis": "oben", "abstand": 20, "umkehren": True}},
])
def test_referenz_gueltig(tmp_path, ref):
    spec = _spec()
    spec["features"].append(ref)
    assert schema_befunde(spec) == [] and plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize("ref", [
    {"id": "R", "typ": "referenz"},                                             # weder achse noch ebene
    {"id": "R", "typ": "referenz", "achse": "y", "ebene": {"basis": "oben"}},   # beides
    {"id": "R", "typ": "referenz", "achse": "w"},
    {"id": "R", "typ": "referenz", "ebene": {"abstand": 5}},                    # basis fehlt
])
def test_referenz_ungueltig(ref):
    spec = _spec()
    spec["features"].append(ref)
    assert schema_befunde(spec) != []


def test_referenz_abstand_muss_positiv_sein(tmp_path):
    spec = _spec()
    spec["features"].append({"id": "R", "typ": "referenz", "ebene": {"basis": "oben", "abstand": -5}})
    assert any(b["pfad"].endswith("ebene.abstand") for b in plausibel_befunde(spec, tmp_path))
