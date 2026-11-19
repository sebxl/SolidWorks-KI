"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 1–2): Maßplan aus Maßprotokoll und Drehprofil."""

import json
from pathlib import Path

import yaml

from swki.zeichnung.massplan import Mass, massplan, massplan_drehteil, massplan_fraesteil

DATEN = Path(__file__).parent / "daten"
REF = Path(__file__).parents[1] / "referenz"


def _spannplatte():
    spec = yaml.safe_load((REF / "stil" / "spannplatte.yaml").read_text(encoding="utf-8"))
    protokoll = json.loads((DATEN / "spannplatte.protokoll.json").read_text(encoding="utf-8"))
    return spec, protokoll


def _nach_name(plan):
    return {m.name: m for m in plan}


def test_fraesteil_anforderungsmasse():
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    erwartet = {"D1@f1_skizze": 200, "D2@f1_skizze": 120, "D1@f1": 20, "D3@t1_skizze": 20, "D1@t1": 12, "D1@r1": 4,
                "D1@g1_positionen": 40, "D2@g1_positionen": 20, "D3@m1": 30, "D1@st_positionen": 150,
                "D2@st_positionen": 20}
    for name, wert in erwartet.items():
        assert plan[name].wert == wert and plan[name].quelle == "modell", name
    assert plan["D3@t1_skizze"].art == "lage" and plan["D1@f1_skizze"].art == "laenge" and plan["D1@r1"].art == "radius"
    assert plan["D3@t1_skizze"].merkmal == "t1" and plan["D1@g1_positionen"].merkmal == "g1"


def test_fraesteil_ohne_hilfs_und_fasenmasse():
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    assert "D1@Ebene1" not in plan and "D1@Ebene2" not in plan and "D1@st_fase" not in plan


def test_ids_eindeutig():
    plan = massplan_fraesteil(*_spannplatte())
    assert len({m.id for m in plan}) == len(plan)


def test_konstruktion_und_mittellinie_weg():
    protokoll = {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "konstruktion", "pfad": "features[0].x", "wert": 5, "bezug": None},
        {"name": "D2@f1_skizze", "art": "lage", "pfad": "features[0].skizze.elemente[1].mittellinie.von[1]", "wert": 5,
         "bezug": "ursprung"},
        {"name": "D3@f1_skizze", "art": "groesse", "pfad": "features[0].skizze.elemente[0].rechteck.breite", "wert": 9,
         "bezug": None}]}]}
    assert [m.name for m in massplan_fraesteil({"features": []}, protokoll)] == ["D3@f1_skizze"]


def _buchse():
    return yaml.safe_load((REF / "buchse" / "buchse.yaml").read_text(encoding="utf-8"))


def test_drehteil_durchmesser_je_einmal():
    plan = massplan_drehteil(_buchse())
    d = sorted(m.wert for m in plan if m.art == "durchmesser")
    assert d == [20, 30, 32, 50]
    assert all(m.quelle == "neu" and m.geometrie for m in plan if m.art == "durchmesser")


def test_drehteil_laengen_von_einem_bezug():
    plan = massplan_drehteil(_buchse())
    laengen = [m for m in plan if m.art == "laenge"]
    assert sorted(m.wert for m in laengen) == [8, 40, 43, 60]
    assert {m.geometrie["von"] for m in laengen} == {0}  # Bundanlage, keine Kette


def test_drehteil_ohne_skizzenmasse():
    plan = massplan(_buchse(), {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "lage", "pfad": "features[0].skizze.elemente[0].polygon.punkte[0][0]",
         "wert": 10, "bezug": "ursprung"}]}, {"id": "f2", "masse": [
        {"name": "D1@f2", "art": "abstand", "pfad": "features[1].abstand", "wert": 1, "bezug": None}]}]})
    namen = {m.name for m in plan if m.quelle == "modell"}
    assert namen == {"D1@f2"} and next(m for m in plan if m.name == "D1@f2").art == "fase"


def test_mass_ist_wertobjekt():
    m = Mass("x", "neu", "laenge", 5.0, "f1")
    assert m.name is None and m.geometrie is None


# --- Review Stufe 2: C1 (Profilarten, Nutgrund, Bohrung auf der Achse), I1 (Doppel nach Lage) -------------------------

def _rot(fid, elemente, schnitt=False):
    f = {"id": fid, "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        *elemente, {"mittellinie": {"von": [0, -5], "bis": [0, 105]}}]}}
    return {**f, "schnitt": True} if schnitt else f


def _poly(*p):
    return {"polygon": {"punkte": [list(x) for x in p]}}


def _welle(*features):
    return {"parameter": {}, "features": list(features)}


def _d(plan):
    return sorted(m.wert for m in plan if m.art == "durchmesser")


def test_kontur_profil_ohne_absturz():
    kontur = {"kontur": {"start": [0, 0], "segmente": [{"linie": [10, 0]}, {"linie": [10, 50]}, {"linie": [0, 50]},
                                                      {"linie": [0, 0]}]}}
    plan = massplan_drehteil(_welle(_rot("f1", [kontur])))
    assert _d(plan) == [20] and [m.wert for m in plan if m.art == "laenge"] == [50]


def test_bohrung_auf_der_achse():
    plan = massplan_drehteil(_welle(_rot("f1", [_poly((0, 0), (15, 0), (15, 60), (0, 60))]),
                                    _rot("f2", [_poly((0, 0), (6, 0), (6, 20), (0, 20))], schnitt=True)))
    assert 12 in _d(plan)


def test_innennut_grund_ist_groesster_radius():
    plan = massplan_drehteil(_welle(_rot("f1", [_poly((10, 0), (20, 0), (20, 60), (10, 60))]),
                                    _rot("f2", [_poly((10, 30), (12, 30), (12, 35), (10, 35))], schnitt=True)))
    assert 24 in _d(plan)


def test_rechteck_einstich():
    plan = massplan_drehteil(_welle(_rot("f1", [_poly((0, 0), (16, 0), (16, 60), (0, 60))]),
                                    _rot("f2", [{"rechteck": {"mitte": [16, 41.5], "breite": 2, "hoehe": 3}}],
                                         schnitt=True)))
    assert 30 in _d(plan)


def test_unbekanntes_element_gemeldet():
    from swki.zeichnung.massplan import massplan_meldungen

    spec = _welle(_rot("f1", [_poly((0, 0), (15, 0), (15, 60), (0, 60))]),
                  _rot("f2", [{"kreis": {"mitte": [15, 30], "durchmesser": 4}}], schnitt=True))
    assert any(m.startswith("MASS_NICHT_GEPLANT") and "f2" in m for m in massplan_meldungen(spec))


def test_doppel_nach_lage_nicht_nach_wert():
    plan = massplan_drehteil(_welle(_rot("f1", [_poly((0, 0), (15, 0), (15, 20), (16, 20), (16, 60), (0, 60))]),
                                    _rot("f2", [_poly((15, 40), (17, 40), (17, 43), (15, 43))], schnitt=True)))
    assert {m.geometrie["bis"] for m in plan if m.art == "laenge"} == {0, 40, 43, 60}
    assert _d(plan).count(30) == 2  # Absatz und Einstichgrund


def test_gleiche_punktmasse_eines_merkmals_nur_einmal():
    """Nutzer 18.11.2026: 47 und 27 (und 10) doppelt – Punkte des Nutpfads auf gleicher Höhe ergeben gleiche Lagemaße."""
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    k1 = sorted((n, m.wert) for n, m in plan.items() if m.merkmal == "k1" and "_pfad" in n)
    werte = [w for _, w in k1]
    assert werte.count(27) == 1 and werte.count(47) == 1 and werte.count(10) == 1, k1


def test_achse_und_modus_je_mass():
    """Nutzer 18.11.2026: Maße an Merkmalen, die in der Ansicht nicht vorhanden sind. Skizzenmaße gehören in die Ansicht
    senkrecht zur Skizzenebene (flach), Tiefenmaße in eine Ansicht quer dazu. Achse 0 = x, 1 = y, 2 = z."""
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    erwartet = {"D3@t1_skizze": (1, "flach"), "D1@t1": (1, "quer"), "D1@k1_pfad": (1, "flach"),
                "D1@k1_skizze": (0, "flach"), "D1@g1_positionen": (1, "flach"), "D1@r1": (1, "flach"),
                "D3@m1": (1, "flach"), "D1@f1_skizze": (1, "flach"), "D1@f1": (1, "quer")}
    for name, (achse, modus) in erwartet.items():
        assert (plan[name].achse, plan[name].modus) == (achse, modus), name


def test_bezug_je_mass():
    """Nutzer 18.11.2026: Mittellinien nur für Maße mit Mittenbezug – der Bezug kommt aus dem Maßprotokoll."""
    plan = _nach_name(massplan_fraesteil(*_spannplatte()))
    assert plan["D2@k1_pfad"].bezug == "ursprung" and plan["D3@t1_skizze"].bezug == "-rand"
    assert plan["D1@f1_skizze"].bezug is None


# --- Stufe 3: Angaben und Textzusätze ---------------------------------------------------------------------------------

def _buchse_protokoll():
    return json.loads((DATEN / "buchse.protokoll.json").read_text(encoding="utf-8"))


def test_angaben_spannplatte():
    plan = massplan_fraesteil(*_spannplatte())
    angaben = {m.merkmal: m for m in plan if m.quelle == "angabe"}
    assert set(angaben) == {"g1", "st"} and angaben["g1"].text.startswith("5 × M6")
    assert (angaben["g1"].achse, angaben["g1"].modus) == (1, "flach")
    teilung = _nach_name(plan)["D3@m1"]
    assert (teilung.praefix, teilung.suffix) == ("4 × ", " (= 120)")


def test_buchse_lochkreis_ersetzt_lage_und_durchmesser():
    plan = massplan(_buchse(), _buchse_protokoll())
    assert [m.text for m in plan if m.quelle == "angabe"] == ["4 × Ø6 – durch\nTK Ø40"]
    assert not [m for m in plan if m.merkmal == "f5" and m.quelle == "modell"]   # Ø6 und Radius 20 entfallen


def test_fase_mit_45_grad():
    plan = massplan(_buchse(), _buchse_protokoll())
    assert {m.suffix for m in plan if m.art == "fase"} == {" × 45°"}


def test_buchse_angabe_achse_aus_kreismuster():
    """Ruling B: Fläche {nahe: …} hat keine Achse – dann die Achse des Kreismusters (y = 1), Ansicht flach."""
    angabe = next(m for m in massplan(_buchse(), _buchse_protokoll()) if m.quelle == "angabe")
    assert (angabe.achse, angabe.modus, angabe.merkmal, angabe.art) == (1, "flach", "f5", "angabe")


def test_angabe_ohne_achse_gemeldet():
    from swki.zeichnung.massplan import massplan_meldungen

    spec = {"parameter": {}, "features": [{"id": "b1", "typ": "bohrung", "flaeche": {"nahe": [0, 0, 0]},
                                           "positionen": [[1, 2]], "durchmesser": 5, "durch": True}]}
    assert "ANGABE_OHNE_ACHSE: b1" in massplan_meldungen(spec)
    assert next(m for m in massplan_fraesteil(spec, {"knoten": []}) if m.quelle == "angabe").achse is None


def test_angabe_meldungen_aus_bohrungsangabe():
    from swki.zeichnung.massplan import massplan_meldungen

    spec = {"parameter": {}, "features": [{"id": "b1", "typ": "bohrung", "flaeche": "oben",
                                           "positionen": [[1, 2]], "durchmesser": 5}]}
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b1") for m in massplan_meldungen(spec))
