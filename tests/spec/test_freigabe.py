import copy
import json

import pytest

from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, freigeben, pruefe_freigabe, pruefsumme

SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "parameter": {"L": 100},
    "features": [{"id": "f1", "typ": "extrusion"}], "pruefung": {"huellquader": [100, 20, 60]},
}


def test_pruefsumme_ignoriert_bauweg():
    anders = copy.deepcopy(SPEC)
    anders["features"] = [{"id": "g1", "typ": "rotation"}]
    anders["max_nachbesserungen"] = 5
    assert pruefsumme(anders) == pruefsumme(SPEC)


@pytest.mark.parametrize("feld", ["parameter", "material", "pruefung", "name"])
def test_pruefsumme_erfasst_anforderungen(feld):
    anders = copy.deepcopy(SPEC)
    anders[feld] = {"x": 1} if feld in ("parameter", "pruefung") else "anders"
    assert pruefsumme(anders) != pruefsumme(SPEC)


def test_freigeben_und_pruefen(tmp_path):
    pfad = tmp_path / "platte.yaml"
    eintrag = freigeben(pfad, SPEC, zeitpunkt="2026-09-27T10:00:00")
    assert eintrag == {"pruefsumme": pruefsumme(SPEC), "freigegeben": "2026-09-27T10:00:00"}
    assert json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))["platte.yaml"] == eintrag
    assert pruefe_freigabe(pfad, SPEC) == eintrag


def test_mehrere_specs_in_einer_freigabe(tmp_path):
    freigeben(tmp_path / "a.yaml", SPEC)
    freigeben(tmp_path / "b.yaml", {**SPEC, "name": "B"})
    assert set(json.loads(freigabe_pfad(tmp_path / "a.yaml").read_text(encoding="utf-8"))) == {"a.yaml", "b.yaml"}


def test_ohne_freigabe(tmp_path):
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(tmp_path / "platte.yaml", SPEC)
    assert e.value.daten["code"] == "FREIGABE_FEHLT"


def test_geaenderte_anforderung(tmp_path):
    pfad = tmp_path / "platte.yaml"
    freigeben(pfad, SPEC)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, {**SPEC, "parameter": {"L": 101}})
    assert e.value.daten["code"] == "FREIGABE_VERALTET"
