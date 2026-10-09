"""huellquader: auto – Soll-Hüllquader aus der Spezifikation (Retro Messstand: Prüfwerte nicht von Hand rechnen)."""

import math
from pathlib import Path

import pytest
import yaml

from swki.pruefung.huellquader import huellquader_auto, seitenpunkt
from swki.spec.ausdruck import auswerten

REFERENZ = Path(__file__).parents[1] / "referenz"


def _platte(**ende):
    return {"id": "f1", "typ": "extrusion",
            "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
            "ende": {"typ": "blind", "tiefe": 10, **ende}}


def _teil(*features, parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {}, "features": [_platte(), *features]}


def _zapfen(fid="f2", flaeche="+y", **ende):
    return {"id": fid, "typ": "extrusion",
            "skizze": {"ebene": {"feature": "f1", "flaeche": flaeche},
                       "elemente": [{"kreis": {"mitte": [30, 0], "durchmesser": 20}}]},
            "ende": {"typ": "blind", "tiefe": 15, **ende}}


def test_platte_allein():
    assert huellquader_auto(_teil()) == ([100, 10, 60], "analytisch")


def test_zapfen_auf_der_oberseite_waechst_nach_oben():
    assert huellquader_auto(_teil(_zapfen()))[0] == [100, 25, 60]


def test_zapfen_auf_der_unterseite_waechst_nach_unten():
    assert huellquader_auto(_teil(_zapfen(flaeche="-y")))[0] == [100, 25, 60]


def test_zapfen_ragt_seitlich_ueber_die_platte():
    zapfen = _zapfen()
    zapfen["skizze"]["elemente"] = [{"kreis": {"mitte": [55, 0], "durchmesser": 20}}]   # x bis 65 statt 50
    assert huellquader_auto(_teil(zapfen))[0] == [115, 25, 60]


def test_schnitte_und_bohrungen_verkleinern_nicht():
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 10}}]}, "ende": {"typ": "durch_alles"}}
    bohrung = {"id": "f3", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 20]],
               "durchmesser": 6, "durch": True}
    assert huellquader_auto(_teil(tasche, bohrung))[0] == [100, 10, 60]


def test_aufsatz_auf_dem_taschenboden():
    """Tasche 6 tief von oben, darin ein Zapfen 4 hoch: der Boden (+y des Schnitts) liegt bei y = 4."""
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 40}}]}, "ende": {"typ": "blind", "tiefe": 6}}
    zapfen = _zapfen("f3", tiefe=20)
    zapfen["skizze"]["ebene"] = {"feature": "f2", "flaeche": "+y"}
    zapfen["skizze"]["elemente"] = [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}]
    assert huellquader_auto(_teil(tasche, zapfen))[0] == [100, 24, 60]   # Boden 4 + 20


def test_mittig_auf_versatzebene_und_rechts():
    steg = {"id": "f2", "typ": "extrusion",
            "skizze": {"ebene": {"versatz": {"ebene": "rechts", "abstand": 60}},
                       "elemente": [{"rechteck": {"mitte": [0, 15], "breite": 8, "hoehe": 30}}]},
            "ende": {"typ": "mittig", "tiefe": 10}}
    # rechts: Z = −u, Y = v; Steg x 55…65, y 0…30, z −4…4
    assert huellquader_auto(_teil(steg))[0] == [115, 30, 60]


def test_umkehren_dreht_den_aufsatz():
    assert huellquader_auto(_teil(_zapfen(umkehren=True, tiefe=8)))[0] == [100, 10, 60]   # wächst in die Platte
    assert huellquader_auto(_teil(_zapfen(umkehren=True)))[0] == [100, 15, 60]   # 15 tief: 5 unten heraus


def test_bis_flaeche_und_versatz_von_flaeche():
    zapfen = _zapfen(flaeche="-y")
    zapfen["skizze"]["ebene"] = {"versatz": {"ebene": "oben", "abstand": 40}}
    zapfen["ende"] = {"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "+y"}, "umkehren": True}
    assert huellquader_auto(_teil(zapfen))[0] == [100, 40, 60]
    zapfen["ende"] = {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "+y"}, "abstand": 5,
                      "umkehren": True}
    assert huellquader_auto(_teil(zapfen))[0] == [100, 40, 60]   # Lücke 10…15, Höhe trotzdem 40


def test_formschraege_groesser_waechst_kleiner_nicht():
    zapfen = _zapfen(formschraege={"winkel": 10, "querschnitt": "groesser"})
    zapfen["skizze"]["elemente"] = [{"kreis": {"mitte": [0, 0], "durchmesser": 20}}]
    zapfen["ende"]["tiefe"] = 15
    zapfen["skizze"]["elemente"] = [{"rechteck": {"mitte": [0, 0], "breite": 98, "hoehe": 58}}]
    zuwachs = 15 * math.tan(math.radians(10))
    assert huellquader_auto(_teil(zapfen))[0] == [pytest.approx(98 + 2 * zuwachs), 25, pytest.approx(58 + 2 * zuwachs)]
    zapfen["ende"]["formschraege"]["querschnitt"] = "kleiner"
    assert huellquader_auto(_teil(zapfen))[0] == [100, 25, 60]


def test_rotation_um_die_v_achse():
    welle = {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[0, 0], [15, 0], [15, 40], [0, 40]]}},
        {"mittellinie": {"von": [0, 0], "bis": [0, 10]}}]}}
    assert huellquader_auto({"features": [welle]})[0] == [30, 40, 30]


def test_rotation_um_die_u_achse_auf_oben():
    welle = {"id": "f1", "typ": "rotation", "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [25, 10], "breite": 50, "hoehe": 8}},
        {"mittellinie": {"von": [0, 0], "bis": [10, 0]}}]}}
    assert huellquader_auto({"features": [welle]})[0] == [50, 28, 28]   # Radius 14 = Außenkante v = 14


def test_muster_und_spiegeln_von_aufsaetzen():
    zapfen = _zapfen()
    muster = {"id": "f3", "typ": "muster_linear", "features": ["f2"],
              "richtung1": {"achse": "z", "abstand": 30, "anzahl": 3}}
    assert huellquader_auto(_teil(zapfen, muster))[0] == [100, 25, 100]   # Zapfen z −10 … 70, Platte ab −30
    spiegel = {"id": "f4", "typ": "spiegeln", "features": ["f3"], "ebene": "vorne"}
    assert huellquader_auto(_teil(zapfen, muster, spiegel))[0] == [100, 25, 140]   # gespiegelt an z = 0: −70 … 70


def test_polygon_mit_eckradius_an_spitzer_ecke():
    """Dreieck mit gerundeter Spitze: die Spitze liegt nicht mehr bei v = 30."""
    r = 5
    dreieck = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[-10, 0], [10, 0], [0, 30]], "radien": [0, 0, r]}}]}, "ende": {"typ": "blind", "tiefe": 5}}
    halbwinkel = math.atan(10 / 30)
    spitze = 30 - r / math.sin(halbwinkel) + r
    assert huellquader_auto({"features": [dreieck]})[0] == [20, pytest.approx(spitze), 5]


def test_kontur_mit_bogen_nach_aussen():
    """Bogen von (10, 0) nach (−10, 0) um (0, 0) gegen den Uhrzeigersinn: Scheitel bei v = 10."""
    halbkreis = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": [
        {"kontur": {"start": [-10, 0], "segmente": [{"linie": [10, 0]}, {"bogen": [-10, 0], "mitte": [0, 0]}]}}]},
        "ende": {"typ": "blind", "tiefe": 5}}
    assert huellquader_auto({"features": [halbkreis]})[0] == [20, 10, 5]


@pytest.mark.parametrize(("feature", "grund"), [
    ({"id": "f2", "typ": "skript", "datei": "skripte/f2.py", "luecke": "x"}, "Skript"),
    ({"id": "f2", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 3}, "Kreismuster"),
    ({**_zapfen(), "skizze": {"ebene": {"nahe": [0, 10, 0]}, "elemente": [{"kreis": {"mitte": [0, 0],
                                                                                    "durchmesser": 5}}]}}, "nahe"),
    ({**_zapfen(), "ende": {"typ": "durch_alles"}}, "durch_alles"),
])
def test_nicht_berechenbar(feature, grund):
    hq, text = huellquader_auto(_teil(feature))
    assert hq is None and grund in text


def _referenz_teile() -> list:
    teile = []
    for datei in sorted(REFERENZ.glob("*/*.yaml")):
        spec = yaml.safe_load(datei.read_text(encoding="utf-8"))
        if spec.get("art") == "teil" and isinstance(spec.get("pruefung", {}).get("huellquader"), list):
            teile.append(pytest.param(spec, id=f"{datei.parent.name}/{datei.stem}"))
    return teile


@pytest.mark.parametrize("spec", _referenz_teile())
def test_referenzteile_wie_live_gemessen(spec):
    """Die Hüllquader der Referenz-Specs sind live bestätigt (Regressions-Suite); auto muss sie treffen oder ablehnen."""
    soll = [auswerten(v, spec.get("parameter", {})) for v in spec["pruefung"]["huellquader"]]
    hq, grund = huellquader_auto(spec)
    if hq is None:
        assert "Skript" in grund or "Verzahnung" in grund
    else:
        assert hq == pytest.approx(soll, abs=1e-6)


def test_seitenpunkt_mittig_steg_mit_formschraege():
    """Steg mittig quer zur Platte skizziert (vorne), 10° kleiner: Oberseite (+y) ist eine Seitenfläche."""
    steg = {"id": "f2", "typ": "extrusion",
            "skizze": {"ebene": "vorne", "elemente": [{"rechteck": {"mitte": [0, 20], "breite": 40, "hoehe": 20}}]},
            "ende": {"typ": "mittig", "tiefe": 12, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
    einzug = 3 * math.tan(math.radians(10))   # Viertel der Tiefe: Mitte der vorderen Hälfte
    assert seitenpunkt(_teil(steg), "f2", "+y") == [0, round(30 - einzug, 3), 3]


def test_seitenpunkt_blind_auf_halber_tiefe():
    zapfen = _zapfen(formschraege={"winkel": 10, "querschnitt": "kleiner"})
    einzug = 7.5 * math.tan(math.radians(10))
    assert seitenpunkt(_teil(zapfen), "f2", "+x") == [round(40 - einzug, 3), 17.5, 0]
