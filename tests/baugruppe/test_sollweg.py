"""Sollweg je Stellung, aufsummierte Drehung, gekoppelte Freiheitsgrade (Spec 4b §5.6) ohne SolidWorks."""

import pytest

from swki.baugruppe.bewegung import (Bewegung, BewegungsMesswerte, Lauf, aufsummiert, bewegungen, bewerte_bewegungen,
                                     drehmatrix, drehung_um)
from tests.baugruppe.beispiel_kopplung import spec as trieb_spec

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
UNTEN = [0, 0, -1]


def _t(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _spec(endlagen: list[dict]) -> dict:
    return {"parameter": {}, "bewegungen": [{"name": "Hub", "grenze": "g1", "erwartet": {"endlagen": endlagen}}]}


HUB = Bewegung("Hub", "g1", "abstand", "schlitten", 0.0, 200.0, 4, ("rad",))


def _lauf(schlitten_x, rad_winkel, fehler=None) -> Lauf:
    stellungen = [0.0, 50.0, 100.0, 150.0, 200.0]
    lagen = [{"schlitten": _t(EINS, (x, 0, 0)), "rad": _t(drehmatrix(UNTEN, w))} for x, w in zip(schlitten_x, rad_winkel)]
    return Lauf("Hub", stellungen=stellungen, lagen=lagen, fehler=fehler, grenze={"oben": False, "unten": None})


def _bewerte(lauf: Lauf, endlagen: list[dict], frei=None, gehalten=None) -> dict:
    m = BewegungsMesswerte(frei or {"schlitten": 2, "rad": 2}, gehalten or {"schlitten": 3, "rad": 3}, [lauf], [])
    pruefungen, _ = bewerte_bewegungen(_spec(endlagen), [HUB], m, 0.1)
    return {p["id"]: p for p in pruefungen}


RAD_ENDLAGE = {"komponente": "rad", "drehung": {"achse": UNTEN, "winkel": 630}}
LINEAR = ([0, 50, 100, 150, 200], [0, 157.5, 315, 472.5, 630])


def test_drehung_um():
    assert drehung_um(drehmatrix((0, 0, 1), 30), (0, 0, 1)) == pytest.approx(30)
    assert drehung_um(drehmatrix((0, 0, 1), 30), (0, 0, -1)) == pytest.approx(-30)
    assert drehung_um(drehmatrix((0, 0, 1), 170), (0, 0, 1)) == pytest.approx(170)


def test_aufsummiert_ueber_360():
    lagen = [{"rad": _t(drehmatrix(UNTEN, w))} for w in LINEAR[1]]
    assert aufsummiert(lagen, "rad", UNTEN) == pytest.approx(LINEAR[1])
    assert aufsummiert(lagen, "fehlt", UNTEN) is None


def test_sollweg_und_endlage_ueber_360_bestanden():
    p = _bewerte(_lauf(*LINEAR), [{"komponente": "schlitten", "verschiebung": [200, 0, 0]}, RAD_ENDLAGE])
    assert p["sollweg:Hub:schlitten"]["ok"] is True and p["sollweg:Hub:rad"]["ok"] is True
    assert p["sollweg:Hub:rad"]["ist"]["groesste_abweichung"] is None
    assert p["endlage:Hub:rad"]["ok"] is True and p["endlage:Hub:rad"]["ist"]["aufsummiert"] == pytest.approx(630)


def test_sollweg_findet_rutschen_in_der_mitte():
    x = [0, 50, 90, 150, 200]  # Endlagen stimmen, Stellung 100 nicht
    p = _bewerte(_lauf(x, LINEAR[1]), [{"komponente": "schlitten", "verschiebung": [200, 0, 0]}, RAD_ENDLAGE])
    assert p["endlage:Hub:schlitten"]["ok"] is True
    s = p["sollweg:Hub:schlitten"]
    assert s["ok"] is False and s["knoten"] == ["schlitten"]
    assert s["ist"]["erste_abweichung"]["stellung"] == 100.0 and s["ist"]["erste_abweichung"]["was"] == "weg"
    # Spec 4b §5.8: größte Abweichung je Komponente mit Betrag (mm)
    groesste = s["ist"]["groesste_abweichung"]
    assert groesste["stellung"] == 100.0 and groesste["was"] == "weg" and groesste["betrag"] == pytest.approx(10)


def test_sollweg_falsche_uebersetzung():
    winkel = [0, 160, 320, 480, 640]  # 160° statt 157,5° je Schritt
    p = _bewerte(_lauf(LINEAR[0], winkel), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is False and p["sollweg:Hub:rad"]["ist"]["erste_abweichung"]["stellung"] == 50.0
    assert p["endlage:Hub:rad"]["ok"] is False and p["endlage:Hub:rad"]["ist"]["aufsummiert"] == pytest.approx(640)
    # die Abweichung wächst bis zur Endstellung: dort liegt die größte (Grad)
    groesste = p["sollweg:Hub:rad"]["ist"]["groesste_abweichung"]
    assert groesste["stellung"] == 200.0 and groesste["was"] == "drehung" and groesste["betrag"] == pytest.approx(10)


def test_sollweg_falsche_drehrichtung():
    p = _bewerte(_lauf(LINEAR[0], [-w for w in LINEAR[1]]), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is False and p["endlage:Hub:rad"]["ok"] is False


def test_verschiebung_in_winkelbewegung_nur_am_ende():
    schwenk = Bewegung("Hub", "g1", "winkel", "rad", 0.0, 90.0, 2)
    lagen = [{"rad": _t(drehmatrix(UNTEN, w), (0, 0, 0))} for w in (0, 45, 90)]
    lauf = Lauf("Hub", stellungen=[0.0, 45.0, 90.0], lagen=lagen, grenze={"oben": False, "unten": None})
    spec = _spec([{"komponente": "rad", "verschiebung": [5, 0, 0]}])
    pruefungen, _ = bewerte_bewegungen(spec, [schwenk], BewegungsMesswerte({"rad": 2}, {"rad": 3}, [lauf], []), 0.1)
    p = {x["id"]: x for x in pruefungen}
    assert p["sollweg:Hub:rad"]["ok"] is True and p["endlage:Hub:rad"]["ok"] is False


def test_abgebrochener_lauf_nicht_geprueft():
    p = _bewerte(_lauf(*LINEAR, fehler={"stellung": 50.0, "meldung": "x"}), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is None and p["endlage:Hub:rad"]["ok"] is None and p["grenze:Hub"]["ok"] is None


def test_freiheitsgrad_gekoppelt():
    p = _bewerte(_lauf(*LINEAR), [RAD_ENDLAGE], frei={"schlitten": 2, "rad": 2}, gehalten={"schlitten": 3, "rad": 2})
    assert p["freiheitsgrad:schlitten"]["ok"] is True
    assert p["freiheitsgrad:rad"]["ok"] is False and "mehr als ein Freiheitsgrad" in p["freiheitsgrad:rad"]["hinweis"]


def test_bewegungen_kennen_die_gekoppelten():
    [hub] = bewegungen(trieb_spec(), {"bewegung_schritte": 8})
    assert hub.komponente == "schlitten" and hub.gekoppelt == ("ritzelwelle", "antriebswelle")


def test_laufbericht_mit_grenze_und_bereich():
    m = BewegungsMesswerte({"schlitten": 2, "rad": 2}, {"schlitten": 3, "rad": 3}, [_lauf(*LINEAR)], [])
    _, bericht = bewerte_bewegungen(_spec([]), [HUB], m, 0.1)
    assert bericht["laeufe"][0]["grenz_id"] == "g1" and bericht["laeufe"][0]["bereich"] == [0.0, 200.0]
