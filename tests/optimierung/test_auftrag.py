"""Block `optimierung` (Spec C2 §2): Schema, Plausibilität, Raum."""

import copy

import pytest

from swki.optimierung.auftrag import auftrag_befunde, lies_auftrag, raum, stellschrauben
from swki.spec.laden import SpecFehler, lade_spec, schema_befunde

from .beispiel import RAMPE, lege_an, rampe


def _meldungen(e) -> str:
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in e.value.daten["befunde"])


def test_gueltiger_auftrag_laedt(tmp_path):
    spec = lade_spec(lege_an(tmp_path))
    a = lies_auftrag(spec, tmp_path / "rampe.yaml")
    assert [s.name for s in a.stellschrauben] == ["H", "v0"]
    h, v0 = a.stellschrauben
    assert (h.datei, h.parameter, h.rahmen, h.bereich) == ("rampe.yaml", "H", (5, 80), (5, 40))
    assert (v0.ablauf, v0.bereich) == ("v0", (0.0, 1.0))      # ohne bereich: der ganze Rahmen
    assert a.modul == tmp_path / "aufgabe_rampe.py"


def test_schema_meldet_unbekanntes_feld_im_block():
    spec = rampe(zielfunktion="x")
    assert any(b["pfad"].startswith("optimierung") for b in schema_befunde(spec))


def test_schema_verlangt_ziel_und_stellschrauben():
    spec = copy.deepcopy(RAMPE)
    del spec["optimierung"]["ziel"]
    assert any("ziel" in b["meldung"] for b in schema_befunde(spec))


@pytest.mark.parametrize("aenderung, text", [
    ({"stellschrauben": [{"name": "X", "parameter": "X", "rahmen": [0, 1]}]}, "Parameter 'X' fehlt"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [5, 80], "bereich": [1, 40]}]}, "bereich"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [50, 80]}]}, "Wert 30"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [80, 5]}]}, "rahmen"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [5, 80]},
                         {"name": "H", "ablauf": "h", "rahmen": [0, 1]}]}, "doppelt"),
    ({"start": [{"H": 200}]}, "start[0].H"),
    ({"start": [{"Q": 1}]}, "keine Stellschraube"),
    ({"pruefaufgabe": {"modul": "fehlt.py"}}, "fehlt.py"),
    ({"szenarien": [{"name": "a", "laeufe": 4, "werte": {}}, {"name": "a", "laeufe": 4, "werte": {}}]}, "doppelt"),
    ({"stellschrauben": [{"name": "H", "spec": "andere.yaml", "parameter": "H", "rahmen": [5, 80]}]}, "andere.yaml"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [5, 80], "schritt": 0.7}], "start": []}, "schritt"),
    ({"stellschrauben": [{"name": "H", "parameter": "H", "rahmen": [5, 80], "schritt": 0.5}],
      "start": [{"H": 10.2}]}, "start[0].H"),
    ({"pruefaufgabe": {"modul": "aufgabe_rampe.py", "abhaengigkeiten": ["fehlt.dat"]}}, "fehlt.dat"),
])
def test_plausibilitaet(tmp_path, aenderung, text):
    with pytest.raises(SpecFehler) as e:
        lade_spec(lege_an(tmp_path, rampe(**aenderung)))
    assert text in _meldungen(e)


def test_stellschraube_auf_ausdruck_ist_befund(tmp_path):
    spec = rampe()
    spec["parameter"]["H"] = "=L/4"            # schon das Teil-Schema lässt nur Zahlen zu; der Block prüft es selbst
    assert "Zahl" in auftrag_befunde(spec["optimierung"], tmp_path, {"r.yaml": spec}, "r.yaml")[0]["meldung"]


def test_auftrag_befunde_baugruppe_kennt_nur_eigene_teile(tmp_path):
    lege_an(tmp_path)
    opt = {"pruefaufgabe": {"modul": "aufgabe_rampe.py"}, "ziel": {"kennzahl": "k", "richtung": "max", "zielwert": 1},
           "stellschrauben": [{"name": "H", "spec": "rampe.yaml", "parameter": "H", "rahmen": [5, 80]},
                              {"name": "Q", "spec": "fremd.yaml", "parameter": "Q", "rahmen": [0, 1]}],
           "szenarien": [{"name": "s", "laeufe": 2, "werte": {}}]}
    b = auftrag_befunde(opt, tmp_path, {"rampe.yaml": lade_spec(tmp_path / "rampe.yaml")}, eigene=None)
    assert [x["pfad"] for x in b] == ["optimierung.stellschrauben[1].spec"]


def test_raum_ohne_bauweg_der_schleife(tmp_path):
    lege_an(tmp_path)
    r1 = raum(rampe(), tmp_path)
    r2 = raum(rampe(budget={"proben": 1}, plateau={"proben": 1}, variante="x", start=[], automatik={},
                    stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80], "bereich": [6, 7]},
                                    {"name": "v0", "ablauf": "v0", "rahmen": [0.0, 1.0]}]), tmp_path)
    assert r1 == r2
    assert r1 != raum(rampe(ziel={"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 0.5}), tmp_path)
    assert "modul_sha256" in r1["pruefaufgabe"]


def test_raum_haengt_am_modulinhalt(tmp_path):
    lege_an(tmp_path)
    r1 = raum(rampe(), tmp_path)
    (tmp_path / "aufgabe_rampe.py").write_text("# geändert\n", encoding="utf-8")
    assert raum(rampe(), tmp_path) != r1


def test_stellschrauben_je_datei():
    s = stellschrauben(RAMPE["optimierung"], eigene="rampe.yaml")
    assert {x.name: x.datei for x in s} == {"H": "rampe.yaml", "v0": None}
