"""Prüfung verzahnungen am Teil (Spec 4b §4.5) ohne SolidWorks: Soll gegen Messwerte, Flankenwahl."""

import math

import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.pruefung.bewertung import Messwerte, bewerte, verzahnung_abweichungen
from swki.pruefung.messen import waehle_flanke
from swki.verzahnung import Stirnrad, Zahnstange

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "verzahnung_mm": 0.005}}
RAD = {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
       "zaehne": "=Z", "breite": 10, "zahndickenabmass": "=AS"}
STANGE = {"id": "z2", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
          "zaehne": 3, "breite": 10, "zahndickenabmass": -0.05}
P = {"M": 2, "Z": 20, "AS": -0.05}


def _rad_ist(**aenderungen) -> dict:
    rad = Stirnrad(2, 20, -0.05)
    ist = {"art": "stirnrad", "kopfkreis": 2 * rad.ra, "fusskreis": 2 * rad.rf, "zaehne": 20, "k": 3,
           "zahnweite": rad.zahnweite()}
    return ist | aenderungen


def _stange_ist(**aenderungen) -> dict:
    st = Zahnstange(2, 3, -0.05)
    ist = {"art": "zahnstange", "zaehne": 3, "kopflinie": [2.0], "teilung": [st.p, st.p], "zahndicke": [st.s] * 3}
    return ist | aenderungen


def test_stirnrad_passt():
    assert verzahnung_abweichungen(RAD, _rad_ist(), P, 0.005) == []


def test_stirnrad_abweichungen():
    soll = Stirnrad(2, 20, -0.05).zahnweite()
    fehler = verzahnung_abweichungen(RAD, _rad_ist(zahnweite=soll + 0.01, zaehne=19), P, 0.005)
    assert fehler == [f"zaehne: ist 19 statt 20", f"zahnweite W3: ist {soll + 0.01} statt {round(soll, 6)}"]
    assert verzahnung_abweichungen(RAD, _rad_ist(kopfkreis=44.01), P, 0.005) == ["kopfkreis: ist 44.01 statt 44.0"]


def test_stirnrad_messfehler_ist_abweichung():
    ist = _rad_ist(fehler="Zahnweite nicht messbar: keine Flankenflächen")
    del ist["zahnweite"]
    assert verzahnung_abweichungen(RAD, ist, P, 0.005) == ["Zahnweite nicht messbar: keine Flankenflächen"]


def test_zahnstange():
    assert verzahnung_abweichungen(STANGE, _stange_ist(), {}, 0.005) == []
    fehler = verzahnung_abweichungen(STANGE, _stange_ist(teilung=[2 * math.pi, 2 * math.pi + 0.02]), {}, 0.005)
    assert len(fehler) == 1 and fehler[0].startswith("teilung:")
    assert verzahnung_abweichungen(STANGE, _stange_ist(kopflinie=[2.0, 2.1]), {}, 0.005)[0].startswith("kopflinie:")


def _spec(*features) -> dict:
    return {"art": "teil", "name": "R", "parameter": P, "features": list(features)}


def _messwerte(verzahnungen: dict) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, verzahnungen=verzahnungen)


def test_bewerte_mit_verzahnung():
    spec = _spec(RAD, STANGE)
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(), "z2": _stange_ist()}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is True and pruefung["knoten"] == []
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(fusskreis=34.9), "z2": "Feature z2 fehlt im Teil"}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is False and pruefung["knoten"] == ["z1", "z2"]
    assert any(m["pruefung"] == "verzahnungen" for m in bericht["maengel"])


def test_ohne_verzahnung_keine_pruefung():
    spec = _spec({"id": "f1", "typ": "referenz", "achse": "z"})
    assert all(p["id"] != "verzahnungen" for p in bewerte(spec, _messwerte({}), STANDARD)["pruefungen"])


def test_waehle_flanke():
    a = Flaeche("sonstige", (10.0, 1.0, 5.0))
    b = Flaeche("sonstige", (10.0, -1.0, 5.0))
    assert waehle_flanke([a, b], (10.05, 0.9, 0.0), (0.0, 0.0, 1.0), 0.5) is a  # z (Achsrichtung) zählt nicht
    with pytest.raises(AnkerFehler, match="keine Flanke"):
        waehle_flanke([a, b], (12.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.5)


# --- Lage aus der aktuellen Spezifikation, Sollwerte aus der freigegebenen Kopie (Fix-Welle 4b, Befund 1) ---

def _rad_feature(abstand, modul=2, zaehne=20) -> dict:
    return {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": abstand}},
            "mitte": [0, 0], "modul": modul, "zaehne": zaehne, "breite": 10, "zahndickenabmass": -0.05}


def _spec_mit(feature: dict | None) -> dict:
    return {"art": "teil", "name": "R", "parameter": {}, "features": [feature] if feature else []}


@pytest.fixture
def gemessen(monkeypatch):
    """Attrappe: _stirnrad/_zahnstange halten die Verzahnung fest, mit der gemessen wurde."""
    from types import SimpleNamespace

    from swki.pruefung import messen

    aufrufe = []
    monkeypatch.setattr(messen, "flaechen", lambda feature: [])
    monkeypatch.setattr(messen.sw, "mathutil", lambda app: object())
    monkeypatch.setattr(messen, "_stirnrad", lambda mu, vz, faces, tol: aufrufe.append(vz) or {"art": "stirnrad"})
    monkeypatch.setattr(messen, "_zahnstange", lambda vz, faces: aufrufe.append(vz) or {"art": "zahnstange"})
    model = SimpleNamespace(FeatureByName=lambda name: object())
    return messen, model, aufrufe


def test_lage_aus_aktueller_spec_geometrie_aus_freigabe(gemessen):
    messen, model, aufrufe = gemessen
    soll, aktuell = _spec_mit(_rad_feature(10)), _spec_mit(_rad_feature(20, modul=3, zaehne=30))
    ergebnis = messen.verzahnungen(model, soll, 0.1, None, aktuell)
    assert ergebnis == {"z1": {"art": "stirnrad"}}
    [vz] = aufrufe
    assert vz.ursprung == (0.0, 0.0, 20.0) and vz.breite == (20.0, 30.0)  # Lage: aktuell (Versatz 20)
    assert (vz.geo.m, vz.geo.z) == (2, 20)  # Sollwerte: freigegebene Kopie


def test_ohne_aktuelle_spec_wie_bisher(gemessen):
    messen, model, aufrufe = gemessen
    messen.verzahnungen(model, _spec_mit(_rad_feature(10)), 0.1, None)
    assert aufrufe[0].ursprung == (0.0, 0.0, 10.0)


def test_feature_fehlt_in_aktueller_spec(gemessen):
    messen, model, aufrufe = gemessen
    ergebnis = messen.verzahnungen(model, _spec_mit(_rad_feature(10)), 0.1, None, _spec_mit(None))
    assert isinstance(ergebnis["z1"], str) and "z1" in ergebnis["z1"] and "aktuellen Spezifikation" in ergebnis["z1"]
    assert aufrufe == []


def test_art_geaendert_in_aktueller_spec(gemessen):
    messen, model, aufrufe = gemessen
    stange = {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
              "zaehne": 3, "breite": 10, "zahndickenabmass": -0.05}
    ergebnis = messen.verzahnungen(model, _spec_mit(_rad_feature(10)), 0.1, None, _spec_mit(stange))
    assert isinstance(ergebnis["z1"], str) and "art" in ergebnis["z1"]
    assert aufrufe == []


# --- _zahnweite: Startpunkte und Richtungen der Strahlen (Befund 6), von Hand gerechnet ---

def test_zahnweite_strahl_auf_der_grundkreistangente(monkeypatch):
    from types import SimpleNamespace

    from swki.compiler.anker import Flaeche
    from swki.pruefung import messen
    from swki.verzahnung import verzahnung_im_teil

    monkeypatch.setattr(messen, "r8_array", lambda werte: [float(x) for x in werte])
    mu = SimpleNamespace(CreatePoint=lambda a: tuple(a), CreateVector=lambda a: tuple(a))
    aufrufe = []

    def flaeche(treffer_ab: int) -> Flaeche:
        zaehler = [0]

        def projiziere(p, v):
            zaehler[0] += 1
            aufrufe.append((p, v))
            return SimpleNamespace(ArrayData=list(p)) if zaehler[0] >= treffer_ab else None

        return Flaeche("sonstige", (0.0, 0.0, 0.0), objekt=SimpleNamespace(_FlagAsMethod=lambda n: None,
                                                                          GetProjectedPointOn=projiziere))

    # Ebene oben: (u, v) -> (x, y, z) = (u, lage, -v); umkehren: Zahnbreite von y = -10 bis 0, Mitte y = -5
    f = {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": "oben", "mitte": [5, 7], "modul": 2, "zaehne": 20,
         "breite": 10, "zahndickenabmass": -0.05, "winkel": 9, "umkehren": True}
    vz = verzahnung_im_teil(f, {})
    # m = 2, z = 20: r_b = 20·cos 20° = 18,793852; r_a = 22 → Start bei t = ±(22 + 5) = ±27
    # k = round(20·20°/180° + 0,5) = 3 → φ_m = 9° + (3 − 1)·180°/20 = 27°
    rb, phi = 18.793852, math.radians(27.0)
    em, ep = (math.cos(phi), math.sin(phi)), (-math.sin(phi), math.cos(phi))
    # rechte Flanke: erster Strahl (t = +27) trifft nicht, zweiter (t = −27) trifft; linke: erster trifft
    messen._zahnweite(mu, vz, flaeche(2), flaeche(1))
    assert len(aufrufe) == 3
    for (p, v), seite in zip(aufrufe, (1, -1, 1)):
        t = seite * 27.0
        start = tuple(c * 1000.0 for c in p)
        assert start[1] == pytest.approx(-5.0, abs=1e-6)  # halbe Zahnbreite
        assert start[0] == pytest.approx(5 + rb * em[0] + t * ep[0], abs=1e-5)
        assert start[2] == pytest.approx(-(7 + rb * em[1] + t * ep[1]), abs=1e-5)
        # Richtung: zur Tangente hin, also −seite·e_p; (u, v) → (x, −z)
        assert v == pytest.approx((-seite * ep[0], 0.0, seite * ep[1]), abs=1e-9)
