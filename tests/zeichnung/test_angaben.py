"""Zeichnungsableitung Z1.3 Stufe 3 Task 2: Angabetexte und Bohrbilder aus der Spec."""

from pathlib import Path

import yaml

from swki.zeichnung.angaben import (Bohrbild, bohrbilder, bohrungsangabe, hinweis_lage, hinweis_lagen, reihenzusatz,
                                    zahl)

REF = Path(__file__).parents[1] / "referenz"


def _lade(pfad: str) -> dict:
    return yaml.safe_load((REF / pfad).read_text(encoding="utf-8"))


def _feature(spec: dict, fid: str) -> dict:
    return next(f for f in spec["features"] if f["id"] == fid)


def test_zahl():
    assert (zahl(6.6), zahl(10.0), zahl(0.5)) == ("6,6", "10", "0,5")


def test_spannplatte_gewinde_reihe():
    spec = _lade("stil/spannplatte.yaml")
    b = bohrbilder(spec)["g1"]
    assert (b.anzahl, b.teilung, b.reihe, b.teilkreis) == (5, 30.0, "m1", None)
    text, meld = bohrungsangabe(_feature(spec, "g1"), spec, b)
    assert text == "5 × M6 – 10 tief\nSenkung Ø6 × 90°" and meld == []
    assert reihenzusatz(b) == ("4 × ", " (= 120)")


def test_spannplatte_stift():
    spec = _lade("stil/spannplatte.yaml")
    text, _ = bohrungsangabe(_feature(spec, "st"), spec, bohrbilder(spec)["st"])
    assert text == "2 × Ø8 – 15 tief\nFase 0,5 × 45°"


def test_buchse_lochkreis():
    spec = _lade("buchse/buchse.yaml")
    b = bohrbilder(spec)["f5"]
    assert (b.anzahl, b.teilkreis) == (4, 40.0)
    assert bohrungsangabe(_feature(spec, "f5"), spec, b)[0] == "4 × Ø6 – durch\nTK Ø40"


def test_zwei_richtungen_und_spiegeln():
    spec = {"parameter": {}, "features": [
        {"id": "f1", "typ": "extrusion"},
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]},
        {"id": "m1", "typ": "muster_linear", "features": ["b1"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3},
         "richtung2": {"achse": "z", "abstand": 10, "anzahl": 2}},
        {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 12 and b.teilung is None and b.reihe is None


def test_unbekannte_groesse_gemeldet():
    f = {"id": "g9", "typ": "normbohrung", "art": "gewinde", "groesse": "M7", "positionen": [[0, 0]], "tiefe": 10}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("g9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNBEKANNT") for m in meld)
    assert "M7" in text


def test_zylinderschraube_durchgang():
    f = {"id": "z1", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M6", "positionen": [[0, 0]],
         "durch": True}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("z1", 2, None, None, None))
    assert text.startswith("2 × Ø6,6 – durch") and meld == []


def test_reihe_im_spiegel():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]},
        {"id": "m1", "typ": "muster_linear", "features": ["b1"], "richtung1": {"achse": "x", "abstand": 30, "anzahl": 5}},
        {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 10 and reihenzusatz(b) == ("4 × ", " (= 120)")


def test_fase_nenn_ohne_gewinde_gemeldet():
    f = {"id": "s9", "typ": "normbohrung", "art": "stift", "groesse": "8", "tiefe": 5, "fase": "nenn",
         "positionen": [[0, 0]]}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("s9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: s9") and "fase" in m for m in meld)


def test_tiefe_fehlt_gemeldet():
    f = {"id": "b9", "typ": "bohrung", "durchmesser": 5, "positionen": [[0, 0]]}
    _, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("b9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b9") and "Tiefe" in m for m in meld)


def test_teilkreis_nicht_bestimmbar_gemeldet():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True},
        {"id": "k1", "typ": "muster_kreis", "features": ["b1"], "achse": "y", "anzahl": 3}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 3 and b.teilkreis is None
    _, meld = bohrungsangabe(spec["features"][0], spec, b)
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b1") and "Teilkreis" in m for m in meld)


# --- Lage des Hinweistexts (Task 4) ----------------------------------------------------------------------------------

def _kreuzt_rechteck(a, b, r) -> bool:
    from swki.zeichnung.lesbarkeit import _schneidet
    return _schneidet(a, b, r)


def test_hinweis_lage_weicht_kante_aus():
    """Plan Task 4 Step 1: Kreis (130, 240) r 1,5 im Umriss (105, 184, 217, 256), Kante waagrecht bei y 245."""
    groesse = (40.0, 9.0)
    kante = ((100.0, 245.0), (220.0, 245.0))
    x, y = hinweis_lage(((130.0, 240.0), 1.5), (105.0, 184.0, 217.0, 256.0), [kante], groesse)
    r = (x - groesse[0] / 2, y - groesse[1] / 2, x + groesse[0] / 2, y + groesse[1] / 2)
    assert not _kreuzt_rechteck(*kante, r)
    assert x > 130 and y > 240


def test_hinweis_lage_ausserhalb_des_umrisses_zuerst():
    """Ohne Hindernis liegt der Text außerhalb des Umrisses, wenn eine Lage das erlaubt (hier über dem Teil)."""
    groesse = (30.0, 9.0)
    x, y = hinweis_lage(((130.0, 240.0), 1.5), (105.0, 184.0, 217.0, 256.0), [], groesse)
    assert y - groesse[1] / 2 >= 256.0


def test_hinweis_lage_unten_bei_bohrung_unter_der_mitte():
    groesse = (30.0, 9.0)
    _, y = hinweis_lage(((130.0, 190.0), 1.5), (105.0, 184.0, 217.0, 256.0), [], groesse)
    assert y < 190


def test_hinweis_lagen_in_fester_reihenfolge_ohne_doppelte():
    lagen = hinweis_lagen(((130.0, 240.0), 1.5), (105.0, 184.0, 217.0, 256.0), [], (30.0, 9.0))
    assert len(lagen) == 16 and len(set(lagen)) == 16
    assert lagen[0] == hinweis_lage(((130.0, 240.0), 1.5), (105.0, 184.0, 217.0, 256.0), [], (30.0, 9.0))


def test_hinweis_text_liegt_neben_der_bohrung():
    """Der Text beginnt am Ende der Hinweislinie und überdeckt die Bohrung nicht."""
    groesse = (40.0, 9.0)
    for x, y in hinweis_lagen(((130.0, 240.0), 1.5), (105.0, 184.0, 217.0, 256.0), [], groesse):
        assert not (x - groesse[0] / 2 <= 130 <= x + groesse[0] / 2 and y - groesse[1] / 2 <= 240 <= y + groesse[1] / 2)


# --- Review-Befunde der Gesamtdurchsicht ------------------------------------------------------------------------------

def _angabe(f: dict, anzahl: int = 1, spec: dict | None = None):
    return bohrungsangabe(f, spec or {"parameter": {}, "features": [f]}, Bohrbild(f["id"], anzahl, None, None, None))


def test_einzelbohrung_ohne_eins_mal():
    f = {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]}
    assert _angabe(f)[0] == "Ø5 – durch"
    assert _angabe(f, 2)[0] == "2 × Ø5 – durch"


def test_gewinde_mit_steigung_iso():
    f = {"id": "g1", "typ": "normbohrung", "art": "gewinde", "groesse": "M12x1.5", "positionen": [[0, 0]], "tiefe": 10}
    assert _angabe(f)[0].startswith("M12 × 1,5 – 10 tief")


def test_bohrung_senkung_als_zeile():
    f = {"id": "b2", "typ": "bohrung", "durchmesser": 6.6, "durch": True, "positionen": [[0, 0]],
         "senkung": {"durchmesser": "=d_s", "tiefe": 6.5}}
    text, meld = _angabe(f, 4, {"parameter": {"d_s": 11}, "features": [f]})
    assert text == "4 × Ø6,6 – durch\nSenkung Ø11 × 6,5 tief" and meld == []


def test_negativer_abstand_ohne_minus():
    assert reihenzusatz(Bohrbild("b", 5, None, -30.0, "m", 5)) == ("4 × ", " (= 120)")


def test_lochkreis_querversatz_gemeldet():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[20, 5]]},
        {"id": "k1", "typ": "muster_kreis", "features": ["b1"], "achse": "y", "anzahl": 3}]}
    _, meld = bohrungsangabe(spec["features"][0], spec, bohrbilder(spec)["b1"])
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b1") and "Winkellage" in m for m in meld)


def test_referenzen_bohrungsangaben_ohne_fehler():
    """Alle Referenz-Teile: keine Ausnahme, kein „1 ×“, jede Senkung einer Bohrung steht im Text."""
    gesehen = 0
    for pfad in sorted(REF.rglob("*.yaml")):
        spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        if not isinstance(spec, dict) or spec.get("art") != "teil":
            continue
        bilder = bohrbilder(spec)
        for f in spec.get("features", []):
            if f.get("typ") not in ("bohrung", "normbohrung"):
                continue
            text, _ = bohrungsangabe(f, spec, bilder[f["id"]])
            gesehen += 1
            assert not text.startswith("1 ×"), (pfad.name, f["id"], text)
            if f.get("senkung"):
                assert "Senkung" in text, (pfad.name, f["id"], text)
    assert gesehen > 5
