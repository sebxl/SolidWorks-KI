"""Zeichnungsableitung Z1.3 Stufe 1 (Plan 2026-11-17 Task 3): Ansichtswahl aus der Spec (R-Kap. 3)."""

from pathlib import Path

import yaml

from swki.zeichnung.ansichten import Ansicht, ist_drehteil, waehle_ansichten

REF = Path(__file__).parents[1] / "referenz"


def _lade(pfad: str) -> dict:
    return yaml.safe_load((REF / pfad).read_text(encoding="utf-8"))


def _welle(innen: float = 0) -> dict:
    return {"parameter": {}, "features": [{"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[innen, 0], [10, 0], [10, 100], [innen, 100]]}},
        {"mittellinie": {"von": [0, -5], "bis": [0, 105]}}]}}]}


def _platte(*bohrungen) -> dict:
    platte = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]}, "ende": {"typ": "blind", "tiefe": 20}}
    return {"parameter": {}, "features": [platte, *bohrungen]}


def _bohrung(fid, flaeche, durch=True):
    return {"id": fid, "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": flaeche}, "positionen": [[0, 0]],
            "durchmesser": 6, **({"durch": True} if durch else {"tiefe": 8})}


def test_drehteil_erkannt():
    assert ist_drehteil(_lade("buchse/buchse.yaml")) and ist_drehteil(_welle())
    assert not ist_drehteil(_lade("stil/spannplatte.yaml"))
    assert ist_drehteil({**_platte(), "verfahren": "drehen"})


def test_buchse_hohl_mit_bundbohrungen():
    a = waehle_ansichten(_lade("buchse/buchse.yaml"))
    haupt = next(x for x in a if x.rolle == "haupt")
    assert haupt == Ansicht("haupt", "*Vorderseite", schnitt=True, winkel_grad=90)
    assert [x.rolle for x in a] == ["haupt", "seite"]
    assert a[1].modellansicht is None  # projiziert aus der Hauptansicht


def test_volle_welle_nur_hauptansicht_ohne_schnitt():
    assert waehle_ansichten(_welle()) == [Ansicht("haupt", "*Vorderseite", schnitt=False, winkel_grad=90)]


def test_hohle_welle_im_schnitt():
    assert waehle_ansichten(_welle(innen=4))[0].schnitt is True


def test_spannplatte_hauptansicht_oben_mit_dickenansicht():
    a = waehle_ansichten(_lade("stil/spannplatte.yaml"))
    assert a[0] == Ansicht("haupt", "*Oben") and [x.rolle for x in a] == ["haupt", "drauf"]


def test_platte_bohrungen_unten():
    assert waehle_ansichten(_platte(_bohrung("b1", "-y"), _bohrung("b2", "-y")))[0].modellansicht == "*Unten"


def test_platte_ohne_innenkontur_kein_schnitt():
    assert not any(x.schnitt for x in waehle_ansichten(_platte(_bohrung("b1", "+y"))))


def test_platte_sackbohrung_von_der_seite_braucht_schnitt():
    a = waehle_ansichten(_platte(_bohrung("b1", "+y"), _bohrung("b2", "+y"), _bohrung("b3", "+x", durch=False)))
    assert a[0].modellansicht == "*Oben" and any(x.schnitt for x in a)
