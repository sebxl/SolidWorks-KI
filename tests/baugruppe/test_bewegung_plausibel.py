"""Stufe 4a: Plausibilität der Bewegungen (Spec 4a §5, Präzisierung 3), Passung des Drehbolzens, Hinweis
pruefaufwand, Vorgaben in config/standard.yaml."""

from types import SimpleNamespace

import pytest

from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_quellen
from swki.baugruppe.plausibel import plausibel_befunde
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, HEBEL, kopie, schreibe


def _befunde(tmp_path, spec, **teile) -> str:
    pfad = schreibe(tmp_path / "A", baugruppe=spec, **teile)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in plausibel_befunde(spec, quellen))


def _v(spec: dict, vid: str) -> dict:
    return next(v for v in spec["verknuepfungen"] if v["id"] == vid)


def test_bewegungsprobe_ohne_befunde(tmp_path):
    assert _befunde(tmp_path, kopie(BAUGRUPPE)) == ""


@pytest.mark.parametrize(("aendern", "erwartet"), [
    (lambda s: _v(s, "g1").update(max=100), "GRENZE_FESTE_ZAHL"),
    (lambda s: _v(s, "g1").pop("max"), "max ist bei grenze_abstand Pflicht"),
    (lambda s: _v(s, "g1").update(min="=HUB", max="=HUB/2"), "muss kleiner als max"),
    (lambda s: _v(s, "g2").update(max="=SCHWENK*5"), "[0, 360]"),
    (lambda s: _v(s, "g1").pop("ausrichtung"), "ausrichtung (gleich | entgegengesetzt) ist bei grenze_abstand Pflicht"),
    (lambda s: _v(s, "v1").update(min=0), "min/max gelten nur bei grenze_abstand/grenze_winkel"),
    (lambda s: _v(s, "s1").pop("anlage_b"), "anlage_b ist bei scharnier Pflicht"),
    (lambda s: _v(s, "s1")["anlage_a"].update(komponente="schieber"), "anlage_a gehört zur Komponente von a"),
    (lambda s: _v(s, "s1")["anlage_b"].update(komponente="hebel", flaeche="+y"), "anlage_b gehört zum Gegenstück"),
    (lambda s: _v(s, "s1").update(a={"komponente": "hebel", "feature": "f1", "flaeche": "+y"}), "a und b sind Achsen"),
    (lambda s: _v(s, "v1").update(anlage_a={"komponente": "schieber", "feature": "f1", "flaeche": "+y"}),
     "anlage_a/anlage_b gelten nur bei scharnier"),
    (lambda s: s["freiheitsgrade"].update(hebel=2), "FREIHEITSGRADE_NICHT_UNTERSTUETZT"),
    (lambda s: s["bewegungen"].pop(1), "BEWEGUNG_FEHLT"),
    (lambda s: s["bewegungen"].append({"name": "Hub2", "grenze": "g1"}), "Grenze g1 treibt schon Hub"),
    (lambda s: s["bewegungen"][1].update(grenze="v1"), "'v1' ist keine grenze_abstand/grenze_winkel"),
    (lambda s: s["freiheitsgrade"].pop("schieber"), "Bewegung Hub: schieber braucht freiheitsgrade: 1"),
    (lambda s: s["bewegungen"][0].update(name="Schwenk"), "Name 'Schwenk' ist doppelt"),
    (lambda s: s["bewegungen"][1]["erwartet"]["endlagen"][0]["drehung"].update(achse=[0, 0, 0]), "Nullvektor"),
    (lambda s: s["bewegungen"][0]["erwartet"]["endlagen"][0].update(komponente="wagen"), "Komponente 'wagen' unbekannt"),
])
def test_befunde(tmp_path, aendern, erwartet):
    spec = kopie(BAUGRUPPE)
    aendern(spec)
    assert erwartet in _befunde(tmp_path, spec)


def test_grenze_nicht_mit_je_position(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "stifte", "quelle": {"normteil": "ISO 8734 8x30"},
                                "je_position": {"komponente": "schieber", "feature": "f2"}})
    _v(spec, "g1")["a"] = {"komponente": "stifte", "referenz": "EINBAU_EBENE_1"}
    assert "nicht mit Komponenten mit je_position" in _befunde(tmp_path, spec)


def test_drehbolzen_braucht_groessere_bohrung(tmp_path):
    hebel = kopie(HEBEL)
    hebel["features"][1]["durchmesser"] = 8
    assert "als Drehbolzen: Bohrung Ø 8 nicht größer als 8" in _befunde(tmp_path, kopie(BAUGRUPPE), hebel=hebel)


def test_drehbolzen_nicht_in_normbohrung(tmp_path):
    hebel = kopie(HEBEL)
    hebel["features"][1] = {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8,
                            "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]], "durch": True}
    assert "braucht eine bohrung" in _befunde(tmp_path, kopie(BAUGRUPPE), hebel=hebel)


def _bg(n: int) -> SimpleNamespace:
    return SimpleNamespace(teile={}, spec={"verknuepfungen": [],
                                           "bewegungen": [{"name": f"B{i}", "grenze": f"g{i}", "schritte": 4}
                                                          for i in range(n)]})


def test_hinweis_pruefaufwand_ab_vier_bewegungen():
    [h] = [x for x in hinweise_baugruppe(_bg(4)) if x["art"] == "pruefaufwand"]
    assert h["pfad"] == "bewegungen"
    assert h["meldung"].startswith("4 Bewegungen: 20 Stellungen in Grundstellung") and "80 mit Paarläufen" in h["meldung"]


def test_kein_hinweis_bei_drei_bewegungen():
    assert [x for x in hinweise_baugruppe(_bg(3)) if x["art"] == "pruefaufwand"] == []


def test_vorgaben_in_standard():
    standard = lade_standard()
    assert (standard["bewegung_schritte"], standard["speicher_grenze_mb"]) == (8, 8000)
