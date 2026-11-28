"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 1–2): Maßplan aus Maßprotokoll und Drehprofil."""

import json
from pathlib import Path

import yaml

from swki.zeichnung.massplan import Mass, massplan, massplan_drehteil, massplan_fraesteil, massplan_meldungen
from swki.zeichnung.toleranzangaben import Toleranz

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


def test_bohrung_tiefe_und_senkung_nur_in_der_angabe():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 6, "tiefe": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [[0, 0]], "senkung": {"durchmesser": 11, "tiefe": 3}}]}
    protokoll = {"knoten": [{"id": "b1", "masse": [
        {"name": "D1@b1_skizze", "art": "durchmesser", "pfad": "features[0].durchmesser", "wert": 6, "bezug": None},
        {"name": "D1@b1", "art": "tiefe", "pfad": "features[0].tiefe", "wert": 8, "bezug": None},
        {"name": "D1@b1_senkung_skizze", "art": "durchmesser", "pfad": "features[0].senkung.durchmesser", "wert": 11,
         "bezug": None},
        {"name": "D1@b1_senkung", "art": "tiefe", "pfad": "features[0].senkung.tiefe", "wert": 3, "bezug": None}]}]}
    plan = massplan_fraesteil(spec, protokoll)
    assert [m.quelle for m in plan] == ["angabe"]
    assert "Senkung Ø11 × 3 tief" in plan[0].text and plan[0].text.startswith("Ø6 – 8 tief")


def test_fase_mit_winkel_suffix_nur_am_abstand():
    spec = {"parameter": {}, "features": [{"id": "fa", "typ": "fase", "abstand": 1, "winkel": 30}]}
    protokoll = {"knoten": [{"id": "fa", "masse": [
        {"name": "D1@fa", "art": "abstand", "pfad": "features[0].abstand", "wert": 1, "bezug": None},
        {"name": "D2@fa", "art": "winkel", "pfad": "features[0].winkel", "wert": 30, "bezug": None}]}]}
    plan = massplan_fraesteil(spec, protokoll)
    assert [(m.name, m.suffix) for m in plan] == [("D1@fa", " × 30°")]
    spec["features"][0].pop("winkel")
    assert massplan_fraesteil(spec, {"knoten": [{"id": "fa", "masse": protokoll["knoten"][0]["masse"][:1]}]})[0].suffix \
        == " × 45°"


# --- Stufe 4 Task 2: Anforderungen im Maßplan ---------------------------------------------------------------------------

def _lade_ref(pfad: str) -> dict:
    return yaml.safe_load((REF / pfad).read_text(encoding="utf-8"))


def _spannplatte_protokoll():
    return _spannplatte()[1]


def test_spannplatte_z_anforderungen():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    plan = massplan(spec, _spannplatte_protokoll())
    stift = next(m for m in plan if m.quelle == "angabe" and m.merkmal == "st")
    assert stift.text.startswith("2 × Ø8 H7 Ⓔ – 15 tief")
    # Nutzer 28.11.2026: Stiftbohrung ohne eigene Rauheit (Sammelrauheit gilt)
    assert {(m.merkmal, m.text) for m in plan if m.quelle == "rauheit"} == {("t1", "Ra 1,6")}
    assert {(m.merkmal, m.form_lage.symbol, m.text) for m in plan if m.quelle == "form_lage"} == {
        ("f1", "<IGTOL-FLAT>", "0,02"), ("t1", "<IGTOL-PARA>", "0,05")}
    assert sorted(m.text for m in plan if m.quelle == "bezug") == ["A", "B"]
    assert {m.anker["flaeche"] for m in plan if m.quelle == "bezug"} == {"-y", "-x"}
    abstand = _nach_name(plan)["D1@st_positionen"]          # Paarabstand 150 aus "=2 * (-A/2)", Parameter A ±0,02
    assert abstand.toleranz == Toleranz(None, 0.02, -0.02, False)
    assert len({m.id for m in plan}) == len(plan)


def test_anforderungseintraege_sind_keine_masse():
    plan = massplan(_lade_ref("zeichnung/spannplatte_z.yaml"), _spannplatte_protokoll())
    for m in plan:
        if m.quelle in ("rauheit", "form_lage", "bezug"):
            assert m.wert == 0.0 and m.name is None and m.art == m.quelle


def test_achse_der_anforderungseintraege():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    next(f for f in spec["features"] if f["id"] == "st")["rauheit"] = {"Ra": 0.8}  # eigene Rauheit an der Bohrung
    plan = massplan(spec, _spannplatte_protokoll())
    ra = {m.merkmal: (m.achse, m.modus) for m in plan if m.quelle == "rauheit"}
    assert ra["st"] == (1, "flach")                         # Bohrung: Achse ihrer Angabe
    assert ra["t1"] == (1, "quer")                          # Schnitt mit Tiefe: Achse der Skizze, Ansicht quer
    fl = {m.merkmal: (m.achse, m.modus) for m in plan if m.quelle == "form_lage"}
    assert fl["f1"] == (1, "quer")                          # Extrusion: Achse der Skizze, Modus quer


def test_buchse_z_passungen():
    plan = massplan(_lade_ref("zeichnung/buchse_z.yaml"), _buchse_protokoll())
    d = {m.wert: m.toleranz for m in plan if m.art == "durchmesser"}
    assert d[20] == Toleranz("H7", None, None, True) and d[32] == Toleranz("k6", None, None, True)
    assert d[50] is None and d[30] is None


def test_toleranz_ohne_mass_gemeldet():
    spec = {**_lade_ref("zeichnung/buchse_z.yaml")}
    spec["toleranzen"] = {**spec["toleranzen"], "L_bund": {"oben": 0.1, "unten": 0}, "GIBTSNICHT": {"passung": "h9"}}
    meld = massplan_meldungen(spec)
    assert "TOLERANZ_OHNE_MASS: GIBTSNICHT" in meld
    assert "TOLERANZ_OHNE_MASS: L_bund" not in meld and "TOLERANZ_OHNE_MASS: D_innen" not in meld
    plan = massplan(spec, _buchse_protokoll())
    assert next(m for m in plan if m.art == "laenge" and m.wert == 8).toleranz == Toleranz(None, 0.1, 0, False)


def test_toleranz_ohne_mass_mit_protokoll():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    spec["toleranzen"] = {**spec["toleranzen"], "GR": {"oben": 0.1, "unten": -0.1}}   # GR steckt im Lagemaß der Gewinde
    assert "TOLERANZ_OHNE_MASS: GR" not in massplan_meldungen(spec, _spannplatte_protokoll())
    spec["toleranzen"] = {**spec["toleranzen"], "NB": {"oben": 0.1, "unten": 0}, "ZZ": {"oben": 0.1, "unten": 0}}
    assert "TOLERANZ_OHNE_MASS: ZZ" in massplan_meldungen(spec, _spannplatte_protokoll())


def test_feature_toleranz_an_schnitt_ohne_mass():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    spec["features"][1]["passung"] = "H8"                    # t1 (schnitt): kein eindeutiges Maß
    assert "TOLERANZ_OHNE_MASS: t1" in massplan_meldungen(spec)


def test_ohne_anforderungen_wie_bisher():
    plan = massplan(*_spannplatte())
    assert all(m.toleranz is None for m in plan) and not [m for m in plan if m.quelle in ("rauheit", "form_lage", "bezug")]
    spec, protokoll = _spannplatte()
    assert not [m for m in massplan_meldungen(spec, protokoll) if m.split(":")[0] in
                ("TOLERANZ_OHNE_MASS", "FORM_LAGE_IT_OHNE_TABELLE", "FUNKTION_UNBESTAETIGT")]


def test_funktion_unbestaetigt_gemeldet():
    assert any(m.startswith("FUNKTION_UNBESTAETIGT: st")
               for m in massplan_meldungen(_lade_ref("zeichnung/spannplatte_z.yaml")))


def test_form_lage_it_ohne_tabelle_gemeldet():
    spec = {"parameter": {}, "features": [{"id": "w1", "typ": "extrusion", "funktion": "lagersitz_welle"}]}
    plan = massplan(spec, {"knoten": []})
    assert "FORM_LAGE_IT_OHNE_TABELLE: w1 rundheit IT4 – keine ISO-286-Tabelle" in massplan_meldungen(spec)
    assert not [m for m in plan if m.quelle == "form_lage"] and [m.text for m in plan if m.quelle == "rauheit"] == ["Ra 0,8"]


def test_parameter_treibt_zwei_masse():
    spec = {"parameter": {"A": 10}, "toleranzen": {"A": {"oben": 0.1, "unten": -0.1}}, "features": [{"id": "f1"}]}
    protokoll = {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "lage", "pfad": "features[0].skizze.elemente[0].kreis.mitte[0]", "wert": 5,
         "bezug": None, "roh": "=A/2"},
        {"name": "D2@f1_skizze", "art": "groesse", "pfad": "features[0].skizze.elemente[0].kreis.durchmesser",
         "wert": 10, "bezug": None, "roh": "=A"}]}]}
    plan = massplan(spec, protokoll)
    assert [m.toleranz for m in plan] == [Toleranz(None, 0.1, -0.1, False)] * 2
    assert len(plan) == 2


# --- Nachbesserung Review Task 2 ----------------------------------------------------------------------------------------

def test_unbekannte_funktion_an_bohrung_stuerzt_nicht_ab():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    next(f for f in spec["features"] if f["id"] == "st")["funktion"] = "gibtsnicht"
    plan = massplan(spec, _spannplatte_protokoll())
    assert any(m.quelle == "angabe" and m.merkmal == "st" for m in plan)
    assert any(m.startswith("FUNKTION_UNBEKANNT: st") for m in massplan_meldungen(spec))


def test_toleranz_mehrdeutig_gemeldet():
    spec = {"parameter": {"A": 10, "AB": 4}, "toleranzen": {"A": {"oben": 0.1, "unten": -0.1},
                                                             "AB": {"oben": 0.2, "unten": -0.2}},
            "features": [{"id": "f1"}]}
    protokoll = {"knoten": [{"id": "f1", "masse": [
        {"name": "D1@f1_skizze", "art": "groesse", "pfad": "features[0].skizze.elemente[0].kreis.durchmesser",
         "wert": 14, "bezug": None, "roh": "=A+AB"}]}]}
    plan = massplan(spec, protokoll)
    assert plan[0].toleranz == Toleranz(None, 0.1, -0.1, False)                 # erster gewinnt
    assert "TOLERANZ_MEHRDEUTIG: D1@f1_skizze: A, AB" in massplan_meldungen(spec, protokoll)
    assert "TOLERANZ_OHNE_MASS: A" not in massplan_meldungen(spec, protokoll)       # AB verliert (erster gewinnt)


def test_toleranz_an_gewinde_ohne_aufnahme_gemeldet():
    spec = {"parameter": {}, "features": [
        {"id": "g1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "positionen": [[0, 0]], "tiefe": 10,
         "flaeche": "oben", "toleranz": {"oben": 0.1, "unten": 0}}]}
    assert "TOLERANZ_OHNE_MASS: g1" in massplan_meldungen(spec)


def test_treibender_parameter_nur_ganze_namen():
    from swki.zeichnung.toleranzangaben import treibender_parameter

    tol = {"A": Toleranz(None, 0.1, -0.1, False)}
    assert [treibender_parameter(r, tol) for r in ("=AB*2", "=TA+1", "=A2", 5, "=A/2")] == [None, None, None, None, "A"]


def test_drehteil_fasenmass_quer_zur_drehachse():
    """Review Task 5 (I5): Das Fasenmaß eines Drehteils gehört in die Ansicht quer zur Drehachse (Längsschnitt); in
    der Stirnansicht setzte D1@f2 an zwei konzentrischen Kreisen an und ließ sich nicht als Zeichnungsmaß setzen."""
    plan = massplan(_lade_ref("zeichnung/buchse_z.yaml"), _buchse_protokoll())
    fasen = [m for m in plan if m.art == "fase"]
    assert fasen and all((m.achse, m.modus) == (1, "quer") for m in fasen)
    platte = massplan(*_spannplatte())
    assert all(m.modus != "quer" or m.art != "fase" for m in platte)


def test_fasenmass_nur_an_rotationskanten_quer(monkeypatch):
    """Nachbesserung C: Nur Fasen an Rotationskanten wandern in die Ansicht quer zur Drehachse – mit bekannter Ansicht
    die Blickrichtung entlang der Drehachse (flach); ohne (Fasen des Drehteils) Kanten eines Rotationsprofils. Eine Fase
    mit anderer Achse, schon quer oder an der Bohrung im Bund bleibt."""
    import swki.zeichnung.massplan as mp

    spec = _lade_ref("zeichnung/buchse_z.yaml")
    spec["features"].append({"id": "fx", "typ": "fase", "kanten": [{"feature": "f5"}], "abstand": 0.5})
    spec["features"].append({"id": "fy", "typ": "fase", "kanten": [{"nahe": [20, 8, 3]}], "abstand": 0.5})
    achse = next(i for i, c in enumerate(mp.achsvektor(spec)) if c)
    andere = (achse + 1) % 3
    fasen = [Mass("D1@fa", "modell", "fase", 0.5, "fa", name="D1@fa", achse=achse, modus="flach"),
             Mass("D1@fb", "modell", "fase", 0.5, "fb", name="D1@fb", achse=andere, modus="flach"),
             Mass("D1@fc", "modell", "fase", 0.5, "fc", name="D1@fc", achse=andere, modus="quer"),
             Mass("D1@fx", "modell", "fase", 0.5, "fx", name="D1@fx"),
             Mass("D1@fy", "modell", "fase", 0.5, "fy", name="D1@fy"),
             Mass("D1@f2", "modell", "fase", 1.0, "f2", name="D1@f2")]
    monkeypatch.setattr(mp, "massplan_fraesteil", lambda s, p, ohne=frozenset(): list(fasen))
    plan = {m.name: (m.achse, m.modus) for m in mp.massplan(spec, _buchse_protokoll()) if m.art == "fase"}
    assert plan == {"D1@fa": (achse, "quer"), "D1@fb": (andere, "flach"), "D1@fc": (andere, "quer"),
                    "D1@fx": (None, None), "D1@fy": (None, None), "D1@f2": (achse, "quer")}


def test_position_nicht_unterstuetzt_in_den_meldungen():
    """Gesamtreview M2: die Meldung geht über `massplan_meldungen` in die Prüfung (Z-TOL-5)."""
    from swki.zeichnung.pruefen import MELDUNG_REGEL

    spec = {"parameter": {}, "features": [{"id": "f1", "typ": "extrusion",
                                           "form_lage": [{"art": "koaxialitaet", "wert": 0.02, "bezug": ["A"]}]}]}
    meldung = next(m for m in massplan_meldungen(spec) if m.startswith("FORM_LAGE_NICHT_UNTERSTUETZT: f1"))
    assert MELDUNG_REGEL[meldung.split(":")[0]] == ("toleranzen", "Z-TOL-5")
    assert [m.form_lage.art for m in massplan(spec, {"knoten": []}) if m.quelle == "form_lage"] == ["koaxialitaet"]
