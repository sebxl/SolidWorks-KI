"""Schnellbau einzelner Features (Spec C1 §3, §4.1): analytisch bekannte Volumen und Lagen, ohne SolidWorks."""

import math

import pytest

pytest.importorskip("build123d")

from swki.schnellbau.fehler import GEOMETRIE, NICHT_UNTERSTUETZT, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue  # noqa: E402
from swki.formschraege import volumen_feature  # noqa: E402
from swki.spec.normen import normmasse  # noqa: E402
from swki.verzahnung import aus_feature  # noqa: E402

KLOTZ = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}}
V0 = 100 * 60 * 20


def spec(*features, parameter=None):
    return {"art": "teil", "name": "probe", "material": "Stahl", "parameter": parameter or {}, "features": [KLOTZ, *features]}


def huelle(t):
    bb = t.solid.bounding_box()
    return [round(c, 6) for c in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)]


def test_extrusion_auf_ebene_oben_wie_modellpunkt():
    t = baue(spec())
    assert t.solid.volume == pytest.approx(V0)
    assert huelle(t) == [-50, 0, -30, 50, 20, 30]      # oben: (u, lage, −v)


def test_parameter_und_setzen():
    s = spec(parameter={"T": 20})
    s["features"][0] = dict(KLOTZ, ende={"typ": "blind", "tiefe": "=T"})
    assert baue(s).solid.volume == pytest.approx(V0)
    assert baue(s, {"T": 10}).solid.volume == pytest.approx(V0 / 2)


def test_umkehren_und_mittig():
    s = spec()
    s["features"][0] = dict(KLOTZ, ende={"typ": "blind", "tiefe": 20, "umkehren": True})
    assert huelle(baue(s))[1::3] == [-20, 0]
    s["features"][0] = dict(KLOTZ, ende={"typ": "mittig", "tiefe": 20})
    assert huelle(baue(s))[1::3] == [-10, 10]


def test_schnitt_auf_flaeche_blind_und_durch_alles():
    loch = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                                                     "elemente": [{"kreis": {"mitte": [10, 5], "durchmesser": 20}}]},
            "ende": {"typ": "blind", "tiefe": 5}}
    assert baue(spec(loch)).solid.volume == pytest.approx(V0 - math.pi * 100 * 5)
    durch = dict(loch, ende={"typ": "durch_alles"})
    assert baue(spec(durch)).solid.volume == pytest.approx(V0 - math.pi * 100 * 20)


def test_schnitt_ohne_material_ist_fehler():
    daneben = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                                                        "elemente": [{"kreis": {"mitte": [300, 0], "durchmesser": 5}}]},
               "ende": {"typ": "blind", "tiefe": 5}}
    with pytest.raises(SchnellbauFehler) as e:
        baue(spec(daneben))
    assert e.value.code == GEOMETRIE and e.value.feature == "f2"


def test_bis_flaeche_und_versatz_von_flaeche():
    zapfen = {"id": "f2", "typ": "extrusion",
              "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": 50}},
                         "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 10}}]},
              "ende": {"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "+y"}, "umkehren": True}}
    assert baue(spec(zapfen)).solid.volume == pytest.approx(V0 + 10 * 10 * 30)
    tasche = {"id": "f2", "typ": "schnitt",
              "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                         "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 10}}]},
              "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "abstand": 4}}
    assert baue(spec(tasche)).solid.volume == pytest.approx(V0 - 10 * 10 * 16)    # Restwand 4 über der Unterseite


def test_polygon_radien_kontur_langloch():
    poly = dict(KLOTZ, skizze={"ebene": "oben", "elemente": [{"polygon": {
        "punkte": [[-50, -30], [50, -30], [50, 30], [-50, 30]], "radien": 5}}]})
    assert baue(spec() | {"features": [poly]}).solid.volume == pytest.approx((6000 - (4 - math.pi) * 25) * 20)
    # Kontur: Rechteck 40 × 20 mit Halbkreis R 10 rechts (gegen den Uhrzeigersinn)
    kontur = dict(KLOTZ, skizze={"ebene": "oben", "elemente": [{"kontur": {"start": [0, -10], "segmente": [
        {"linie": [40, -10]}, {"bogen": [40, 10], "mitte": [40, 0]}, {"linie": [0, 10]}, {"linie": [0, -10]}]}}]})
    assert baue(spec() | {"features": [kontur]}).solid.volume == pytest.approx((800 + math.pi * 50) * 20)
    langloch = dict(KLOTZ, skizze={"ebene": "oben", "elemente": [{"langloch": {
        "mitte": [0, 0], "laenge": 30, "breite": 10, "winkel": 30}}]})
    assert baue(spec() | {"features": [langloch]}).solid.volume == pytest.approx((300 + math.pi * 25) * 20)


def test_geschachtelte_konturen_gerade_ungerade():
    ring = dict(KLOTZ, skizze={"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 40}},
                                                              {"kreis": {"mitte": [0, 0], "durchmesser": 20}}]})
    assert baue(spec() | {"features": [ring]}).solid.volume == pytest.approx(math.pi * (400 - 100) * 20)


def test_rotation_um_mittellinie():
    huelse = {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[10, 0], [16, 0], [16, 40], [10, 40]]}},
        {"mittellinie": {"von": [0, -5], "bis": [0, 45]}}]}}
    t = baue({"art": "teil", "name": "h", "parameter": {}, "features": [huelse]})
    assert t.solid.volume == pytest.approx(math.pi * (256 - 100) * 40)
    assert huelle(t) == [-16, 0, -16, 16, 40, 16]
    nut = {"id": "f2", "typ": "rotation", "schnitt": True, "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[15, 20], [17, 20], [17, 23], [15, 23]]}},
        {"mittellinie": {"von": [0, -5], "bis": [0, 45]}}]}}
    t = baue({"art": "teil", "name": "h", "parameter": {}, "features": [huelse, nut]})
    assert t.solid.volume == pytest.approx(math.pi * (256 - 100) * 40 - math.pi * (256 - 225) * 3)


def test_verrundung_senkrechte_kanten_eines_features():
    r = 5
    f = {"id": "f2", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": r}
    assert baue(spec(f)).solid.volume == pytest.approx(V0 - 4 * (r * r - math.pi * r * r / 4) * 20)


def test_senkrechte_kanten_nur_vom_rand_des_features():
    """Die Wände einer späteren Tasche liegen im Werkzeug von f1, gehören aber nicht zu f1 (Formplatte f4/f5)."""
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 10}}
    aussen = {"id": "f3", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    innen = {"id": "f4", "typ": "verrundung", "kanten": [{"feature": "f2", "auswahl": "senkrechte_kanten"}], "radius": 3}
    soll = V0 - 4 * (25 - math.pi * 25 / 4) * 20 - (800 - 4 * (9 - math.pi * 9 / 4)) * 10
    assert baue(spec(tasche, aussen, innen)).solid.volume == pytest.approx(soll)


def test_fase_einzelkante_und_tangential_fortgesetzt():
    eine = {"id": "f2", "typ": "fase", "kanten": [{"nahe": [0, 20, 30]}], "abstand": 1}
    assert baue(spec(eine)).solid.volume == pytest.approx(V0 - 0.5 * 100)
    # gerundeter Umriss: die Fase an einer Kante läuft über den ganzen oberen Rand (Pappus, Schwerpunkt 1/3 innen)
    R = 10
    rund = dict(KLOTZ, skizze={"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100,
                                                                           "hoehe": 60, "radius": R}}]})
    fase = {"id": "f2", "typ": "fase", "kanten": [{"nahe": [0, 20, 30]}], "abstand": 1}
    basis = (6000 - (4 - math.pi) * R * R) * 20
    pfad = 2 * (100 - 2 * R) + 2 * (60 - 2 * R) + 2 * math.pi * (R - 1 / 3)
    assert baue(spec() | {"features": [rund, fase]}).solid.volume == pytest.approx(basis - 0.5 * pfad, rel=1e-9)


def _bohrung_m(typ: str, d: float, tiefe: float) -> float:
    r = d / 2
    return math.pi * r * r * tiefe + math.pi * r * r * (r / math.tan(math.radians(59))) / 3


def test_normbohrung_gewinde_blind_und_zylinderschraube_durch():
    m5 = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M5",
          "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0], [20, 0]], "tiefe": 12, "gewindetiefe": 10}
    k = normmasse("gewinde", "M5")["kernloch"]
    t = baue(spec(m5))
    assert t.solid.volume == pytest.approx(V0 - 2 * _bohrung_m("gewinde", k, 12))
    assert [tuple(round(c, 9) for c in p) for p in t.features["f2"].punkte] == [(0, 20, 0), (20, 20, 0)]
    assert t.features["f2"].richtung == (0, -1, 0)
    m3 = {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M3",
          "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]], "durch": True}
    m = normmasse("zylinderschraube", "M3")
    soll = math.pi * (m["senkung_d"] / 2) ** 2 * m["senkung_t"] + math.pi * (m["durchgang"] / 2) ** 2 * (20 - m["senkung_t"])
    assert baue(spec(m3)).solid.volume == pytest.approx(V0 - soll)


def test_bohrung_mit_flachsenkung_auf_naher_flaeche():
    b = {"id": "f2", "typ": "bohrung", "flaeche": {"nahe": [0, 20, 0]}, "positionen": [[0, 0]], "durchmesser": 6.6,
         "durch": True, "senkung": {"durchmesser": 11, "tiefe": 6.8}}
    soll = math.pi * 5.5 ** 2 * 6.8 + math.pi * 3.3 ** 2 * (20 - 6.8)
    assert baue(spec(b)).solid.volume == pytest.approx(V0 - soll)


LOCH = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-30, 10]],
        "durchmesser": 4, "durch": True}
V_LOCH = math.pi * 4 * 20


def test_muster_linear_und_spiegeln():
    muster = {"id": "f3", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 15, "anzahl": 4}}
    t = baue(spec(LOCH, muster))
    assert t.solid.volume == pytest.approx(V0 - 4 * V_LOCH)
    assert huelle(t) == [-50, 0, -30, 50, 20, 30]
    spiegel = {"id": "f4", "typ": "spiegeln", "features": ["f2", "f3"], "ebene": "vorne"}
    assert baue(spec(LOCH, muster, spiegel)).solid.volume == pytest.approx(V0 - 8 * V_LOCH)
    zwei = {"id": "f3", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 15, "anzahl": 3},
            "richtung2": {"achse": "z", "abstand": 8, "anzahl": 2, "umkehren": True}}
    assert baue(spec(LOCH, zwei)).solid.volume == pytest.approx(V0 - 6 * V_LOCH)


def test_muster_kreis_gleich_verteilt():
    loch = dict(LOCH, positionen=[[20, 0]])
    kreis = {"id": "f3", "typ": "muster_kreis", "features": ["f2"], "achse": "y", "anzahl": 4}
    t = baue(spec(loch, kreis))
    assert t.solid.volume == pytest.approx(V0 - 4 * V_LOCH)


def test_referenz_ebene_und_achse():
    e = {"id": "TRENN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": 12}}
    u = {"id": "UNTEN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": 3, "umkehren": True}}
    a = {"id": "ACHSE", "typ": "referenz", "achse": "z"}
    t = baue(spec(e, u, a))
    assert (t.features["TRENN"].ebene.orientierung, t.features["TRENN"].ebene.lage) == ("oben", 12)
    assert t.features["UNTEN"].ebene.lage == -3
    assert t.features["ACHSE"].richtung == (0, 0, 1)


@pytest.mark.parametrize(("ende", "abstand"), [({"typ": "blind", "tiefe": 10}, 20), ({"typ": "mittig", "tiefe": 10}, 25)])
@pytest.mark.parametrize("querschnitt", ["kleiner", "groesser"])
def test_formschraege_wie_analytisches_volumen(ende, abstand, querschnitt):
    """Zapfen sitzt genau auf der Oberseite (y 20): blind ab y 20, mittig um y 25."""
    zapfen = {"id": "f2", "typ": "extrusion", "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": abstand}},
                                                        "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 20}}]},
              "ende": dict(ende, formschraege={"winkel": 5, "querschnitt": querschnitt})}
    soll, _ = volumen_feature(zapfen, {})
    assert baue(spec(zapfen)).solid.volume == pytest.approx(V0 + soll, rel=1e-6)


def test_formschraege_schnitt_rechteck_kleiner():
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                                                      "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 20}}]},
              "ende": {"typ": "blind", "tiefe": 8, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
    soll, _ = volumen_feature(tasche, {})
    assert baue(spec(tasche)).solid.volume == pytest.approx(V0 - soll, rel=1e-6)


def test_verzahnung_stirnrad_flaeche_mal_breite():
    z = {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
         "zaehne": 20, "breite": 10, "zahndickenabmass": -0.05}
    t = baue({"art": "teil", "name": "rad", "parameter": {}, "features": [z]})
    assert t.solid.volume == pytest.approx(aus_feature(z, {}).flaeche() * 10, rel=2e-4)
    assert t.features["z1"].punkte and tuple(t.features["z1"].punkte[0]) == (0, 0, 0)


def test_skript_ist_nicht_unterstuetzt():
    s = spec({"id": "f2", "typ": "skript", "datei": "x.py", "luecke": "Gewinde"})
    with pytest.raises(SchnellbauFehler) as e:
        baue(s)
    assert e.value.code == NICHT_UNTERSTUETZT and e.value.feature == "f2"
