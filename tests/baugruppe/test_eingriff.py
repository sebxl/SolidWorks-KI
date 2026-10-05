"""Prüfung eingriff:<kopplung> und unterdrückte Verknüpfungen (Spec 4b §5.5), Kopplungen im Bericht – ohne SolidWorks."""

import pytest

from swki.baugruppe.bewertung import BaugruppenMesswerte, _eingriff, _verknuepfungen
from swki.pruefung.bericht import bericht_markdown
from tests.baugruppe.beispiel_kopplung import quellen, spec

EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
GELESEN = {"k1": {"durchmesser": 40.0, "art": 0, "umkehren": False},
           "k2": {"zaehler": 100.0, "nenner": 50.0, "umkehren": False}}


def _lage(x, y, z=0.0) -> list[float]:
    return EINS[:9] + [x / 1000, y / 1000, z / 1000] + EINS[12:]


def _messwerte(lagen=None, gelesen=None, **weitere) -> BaugruppenMesswerte:
    lagen = {"zahnstange": _lage(0, 0, 10), "ritzelwelle": _lage(37.3, 20), "antriebswelle": _lage(112.3, 20)} | (lagen or {})
    return BaugruppenMesswerte(rebuild_fehler=[], verknuepfungen={}, komponenten={}, stueckliste={}, interferenzen=[],
                               box=[0.0] * 6, masse_kg=1.0, lagen=lagen,
                               kopplungen=GELESEN if gelesen is None else gelesen, **weitere)


def _pruefe(m) -> tuple[dict, list[dict]]:
    pruefungen, bericht = _eingriff(spec(), quellen(), m, 0.005)
    return {p["id"]: p for p in pruefungen}, bericht


def test_eingriff_in_ordnung():
    p, bericht = _pruefe(_messwerte())
    assert p["eingriff:k1"]["ok"] is True and p["eingriff:k2"]["ok"] is True
    assert p["eingriff:k1"]["ist"]["achsabstand"] == pytest.approx(20.0)
    assert [(b["kopplung"], b["soll"], b["achsabstand"], b["ueberdeckung"]) for b in bericht] == [
        ("k1", "Ø 40", 20.0, 10.0), ("k2", "100:50", 75.0, 10.0)]


def test_achsabstand_falsch():
    p, _ = _pruefe(_messwerte({"antriebswelle": _lage(112.4, 20)}))
    assert p["eingriff:k2"]["ok"] is False and p["eingriff:k2"]["knoten"] == ["k2"]
    assert "Achsabstand 75.1 statt 75 mm" in p["eingriff:k2"]["hinweis"]


def test_uebersetzung_und_teilkreis_falsch():
    gelesen = {"k1": {"durchmesser": 40.5, "art": 0, "umkehren": False},
               "k2": {"zaehler": 110.0, "nenner": 50.0, "umkehren": False}}
    p, _ = _pruefe(_messwerte(gelesen=gelesen))
    assert p["eingriff:k1"]["hinweis"] == "Teilkreis 40.5 statt 40 mm"
    assert p["eingriff:k2"]["hinweis"] == "Übersetzung 110:50 statt 100:50"


def test_vertauschte_uebersetzung_ist_in_ordnung():
    # Spike S14b Zeile 6: SolidWorks liefert Zähler und Nenner vertauscht zurück (gesetzt 100/50, gelesen 50/100)
    gelesen = {"k1": GELESEN["k1"], "k2": {"zaehler": 50.0, "nenner": 100.0, "umkehren": False}}
    p, _ = _pruefe(_messwerte(gelesen=gelesen))
    assert p["eingriff:k2"]["ok"] is True and p["eingriff:k2"]["knoten"] == []


def test_fehlende_kopplung_meldet_nur_verknuepfungen():
    p, _ = _pruefe(_messwerte(gelesen={"k1": GELESEN["k1"]}))
    assert p["eingriff:k2"]["ok"] is True


def test_waelzpunkt_und_breite():
    p, _ = _pruefe(_messwerte({"ritzelwelle": _lage(300, 20), "antriebswelle": _lage(375, 20)}))
    assert p["eingriff:k1"]["hinweis"] == "Wälzpunkt außerhalb der Zahnstange" and p["eingriff:k2"]["ok"] is True
    p, _ = _pruefe(_messwerte({"zahnstange": _lage(0, 0, 30)}))
    assert p["eingriff:k1"]["hinweis"] == "Zahnbreiten überdecken sich nicht"


def test_komponente_fehlt():
    m = _messwerte()
    del m.lagen["antriebswelle"]
    p, _ = _pruefe(m)
    assert p["eingriff:k2"]["ok"] is False and p["eingriff:k2"]["hinweis"] == "Komponente fehlt in der Baugruppe"


def test_unterdrueckte_verknuepfung_ist_fehlerhaft():
    s = spec()
    m = _messwerte(unterdrueckt=["k2"])
    m.verknuepfungen = {v["id"]: 0 for v in s["verknuepfungen"]} | {"s1.anlage": 0, "s2.anlage": 0}
    e = _verknuepfungen(s, quellen(), m)
    assert e["ok"] is False and e["ist"]["fehlerhaft"] == {"k2": "unterdrückt"} and e["knoten"] == ["k2"]


def test_bericht_kopplungen():
    zeilen = [{"kopplung": "k1", "typ": "zahnstange", "a": "ritzelwelle", "b": "zahnstange", "soll": "Ø 40",
               "gelesen": GELESEN["k1"], "achsabstand": 20.0, "achsabstand_soll": 20.0, "ueberdeckung": 10.0},
              {"kopplung": "k2", "typ": "zahnrad", "a": "antriebswelle", "b": "ritzelwelle", "soll": "100:50",
               "gelesen": "Kopplung k2 nicht lesbar: x", "achsabstand": 75.0, "achsabstand_soll": 75.0, "ueberdeckung": 10.0}]
    text = bericht_markdown(spec(), "A", [], ("pruefen", "…"), {"maengel": [], "bilder": {}, "kopplungen": zeilen},
                            None, None, [])
    assert "## Kopplungen (letzter Lauf)" in text
    assert "| k1 | zahnstange | ritzelwelle → zahnstange | Ø 40 | Ø 40 | 20 / 20 | 10 |" in text
    assert "| k2 | zahnrad | antriebswelle → ritzelwelle | 100:50 | Kopplung k2 nicht lesbar: x | 75 / 75 | 10 |" in text


@pytest.mark.parametrize("gelesen", [{"zaehler": 0.0, "nenner": 50.0}, {"zaehler": 100.0, "nenner": 0.0},
                                     {"zaehler": 0.0, "nenner": 0.0}])
def test_uebersetzung_null_ist_nicht_lesbar(gelesen):
    # SolidWorks liefert Zähler oder Nenner 0: kein ZeroDivisionError, sondern ein Mangel an dieser Kopplung
    p, _ = _pruefe(_messwerte(gelesen={"k1": GELESEN["k1"], "k2": gelesen | {"umkehren": False}}))
    assert p["eingriff:k2"]["ok"] is False and "Übersetzung nicht lesbar" in p["eingriff:k2"]["hinweis"]
    assert p["eingriff:k2"]["knoten"] == ["k2"] and p["eingriff:k1"]["ok"] is True
