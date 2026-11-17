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


def test_buchse_hohl_vollschnitt_aus_stirnansicht():
    """Hohles Drehteil: Stirnansicht (Blick entlang der Achse) als Modellansicht, Hauptansicht = Längsschnitt A-A
    daraus (Live Z1.3: Skizzen in gedrehten Ansichten landen nicht in Blattkoordinaten)."""
    a = waehle_ansichten(_lade("buchse/buchse.yaml"))
    assert a == [Ansicht("seite", "*Oben"), Ansicht("haupt", None, schnitt=True)]


def test_hohle_welle_ohne_bohrungen_auch_aus_stirnansicht():
    assert waehle_ansichten(_welle(innen=4)) == [Ansicht("seite", "*Oben"), Ansicht("haupt", None, schnitt=True)]


def test_volle_welle_nur_hauptansicht_ohne_schnitt():
    assert waehle_ansichten(_welle()) == [Ansicht("haupt", "*Vorderseite", schnitt=False, winkel_grad=90)]




def test_spannplatte_drei_ansichten():
    """Nutzer 17.11.2026: meist 3–4 Ansichten; Frästeil-Grundsatz haupt + drauf + seite (Stufe 2, Task 4)."""
    a = waehle_ansichten(_lade("stil/spannplatte.yaml"))
    assert a[0] == Ansicht("haupt", "*Oben") and [x.rolle for x in a] == ["haupt", "drauf", "seite"]


def test_weitere_rollen():
    from swki.zeichnung.ansichten import weitere_rollen

    assert weitere_rollen(_lade("stil/spannplatte.yaml")) == ["seite_rechts", "unter"]
    assert weitere_rollen(_lade("buchse/buchse.yaml")) == []


def test_platte_bohrungen_unten():
    assert waehle_ansichten(_platte(_bohrung("b1", "-y"), _bohrung("b2", "-y")))[0].modellansicht == "*Unten"


def test_platte_ohne_innenkontur_kein_schnitt():
    assert not any(x.schnitt for x in waehle_ansichten(_platte(_bohrung("b1", "+y"))))


def test_platte_sackbohrung_von_der_seite_braucht_schnitt():
    a = waehle_ansichten(_platte(_bohrung("b1", "+y"), _bohrung("b2", "+y"), _bohrung("b3", "+x", durch=False)))
    assert a[0].modellansicht == "*Oben" and any(x.schnitt for x in a)


def _welle_quer(innen: float = 0) -> dict:
    """Welle mit Mittellinie entlang u (Achse X): Radius ist |v| (Review I2)."""
    return {"parameter": {}, "features": [{"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[5, innen], [105, innen], [105, 10], [5, 10]]}},
        {"mittellinie": {"von": [0, 0], "bis": [110, 0]}}]}}]}


def test_welle_achse_u_voll_ohne_schnitt():
    assert waehle_ansichten(_welle_quer()) == [Ansicht("haupt", "*Vorderseite", schnitt=False, winkel_grad=0)]


def test_welle_achse_u_hohl_schnitt_aus_stirn():
    assert waehle_ansichten(_welle_quer(innen=4)) == [Ansicht("seite", "*Rechts"), Ansicht("haupt", None, schnitt=True)]


def test_drehen_ohne_rotation_wie_fraesteil_mit_hinweis():
    from swki.zeichnung.ansichten import hinweise

    spec = {"verfahren": "drehen", "parameter": {}, "features": [{"id": "f1", "typ": "extrusion", "skizze": {
        "ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 8}}]}, "ende": {"typ": "blind", "tiefe": 20}}]}
    assert waehle_ansichten(spec)[0].rolle == "haupt"
    assert any("Rotation" in h for h in hinweise(spec))
    assert waehle_ansichten({"verfahren": "drehen", "features": []})  # kein IndexError


def test_platte_sackbohrung_von_gegenseite_braucht_schnitt():
    a = waehle_ansichten(_platte(_bohrung("b1", "+y"), _bohrung("b2", "+y"), _bohrung("b3", "+y"),
                                 _bohrung("b4", "-y", durch=False)))
    assert a[0].modellansicht == "*Oben" and any(x.schnitt for x in a)


def test_vorzug_hauptansicht_fuer_merkmale_der_hauptseite():
    from swki.zeichnung.ansichten import vorzugsansichten
    from swki.zeichnung.massplan import Mass

    spec = _lade("stil/spannplatte.yaml")
    plan = [Mass(n, "modell", "lage", 1.0, f, name=n) for n, f in
            (("D1@g1_positionen", "g1"), ("D1@st_positionen", "st"), ("D3@t1_skizze", "t1"), ("D1@f1_skizze", "f1"),
             ("D3@k1_skizze", "k1"))]
    v = vorzugsansichten(spec, plan)
    assert v == {"D1@g1_positionen": "haupt", "D1@st_positionen": "haupt", "D3@t1_skizze": "haupt",
                 "D1@f1_skizze": "haupt"}


def test_vorzug_muster_erbt_richtung_der_quelle():
    from swki.zeichnung.ansichten import vorzugsansichten
    from swki.zeichnung.massplan import Mass

    v = vorzugsansichten(_lade("stil/spannplatte.yaml"), [Mass("D3@m1", "modell", "abstand", 30.0, "m1", name="D3@m1")])
    assert v == {"D3@m1": "haupt"}


def test_vorzug_verrundung_erbt_richtung_des_kantenfeatures():
    """Review I4: r1 (Eckradien der Tasche t1) gehört wie t1 in die Hauptansicht."""
    from swki.zeichnung.ansichten import vorzugsansichten
    from swki.zeichnung.massplan import Mass

    v = vorzugsansichten(_lade("stil/spannplatte.yaml"), [Mass("D1@r1", "modell", "radius", 4.0, "r1", name="D1@r1")])
    assert v == {"D1@r1": "haupt"}
