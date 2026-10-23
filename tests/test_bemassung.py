import pytest

from swki.bemassung import Auftrag, Kennpunkt, bezug_von, massplan, paare_mitte, rechteck_kennkoordinate

TOL = 1e-3
LOCH = "kreis 8"


def punkt(u, v, bezug_u="ursprung", bezug_v="ursprung", gruppe=LOCH):
    return Kennpunkt(uv=(u, v), bezug={0: bezug_u, 1: bezug_v}, gruppe=gruppe)


def plan(punkte, lagen=None):
    lagen = lagen or {}
    return massplan(punkte, lambda p, a: lagen[(p, a)], TOL)


def gleich(ist, soll):
    """Aufträge als Liste vergleichen, Reihenfolge egal."""
    assert len(ist) == len(soll), ist
    for a in soll:
        assert a in ist, f"{a} fehlt in {ist}"


def test_bezug_von_vorgabe_ursprung():
    assert bezug_von({}) == {0: "ursprung", 1: "ursprung"}
    assert bezug_von({"bezug": {"u": "-rand"}}) == {0: "-rand", 1: "ursprung"}
    assert bezug_von({"bezug": {"v": {"flaeche": "+x"}}}) == {0: "ursprung", 1: {"flaeche": "+x"}}


def test_mitte_zwei_bohrungen_rand_und_symmetrie():
    punkte = [punkt(-70, 20, "-rand", "mitte"), punkt(-70, -20, "-rand", "mitte")]
    ist = plan(punkte, {(0, 0): -80.0})
    gleich(ist, [
        Auftrag("symmetrie", 0, 1, partner=1),
        Auftrag("paarabstand", 0, 1, partner=1, wert=40),
        Auftrag("bezug", 0, 0, bezug="-rand", wert=10),
    ])


def test_mitte_2x2_ohne_ueberbestimmung():
    punkte = [punkt(30, 20, "mitte", "mitte"), punkt(-30, 20, "mitte", "mitte"),
              punkt(30, -20, "mitte", "mitte"), punkt(-30, -20, "mitte", "mitte")]
    ist = plan(punkte)
    assert len(ist) == 5
    assert [a for a in ist if a.art == "symmetrie"].__len__() == 3
    assert sorted((a.punkt, a.partner) for a in ist if a.art == "symmetrie") == [(0, 1), (0, 2), (1, 3)]
    assert Auftrag("paarabstand", 0, 0, partner=1, wert=60) in ist
    assert Auftrag("paarabstand", 0, 1, partner=2, wert=40) in ist
    assert not [a for a in ist if a.art in ("ursprung", "ausrichtung", "deckung", "bezug")]


def test_mitte_drei_punkte_paar_und_mittelpunkt():
    punkte = [punkt(-20, 5, "mitte"), punkt(0, 5, "mitte"), punkt(20, 5, "mitte")]
    ist = plan(punkte)
    gleich(ist, [
        Auftrag("symmetrie", 0, 0, partner=2),
        Auftrag("paarabstand", 0, 0, partner=2, wert=40),
        Auftrag("ausrichtung", 1, 0),
        Auftrag("ursprung", 0, 1, wert=5),
        Auftrag("ursprung", 1, 1, wert=5),
    ])


def test_mitte_alle_auf_null_nur_ausrichtung():
    punkte = [punkt(-10, 0, "mitte", "mitte"), punkt(10, 0, "mitte", "mitte")]
    ist = plan(punkte)
    gleich(ist, [
        Auftrag("symmetrie", 0, 0, partner=1),
        Auftrag("paarabstand", 0, 0, partner=1, wert=20),
        Auftrag("ausrichtung", 0, 1),
    ])


def test_paare_nur_in_gleicher_gruppe():
    punkte = [punkt(-30, 0, "mitte", gruppe="kreis 8"), punkt(30, 0, "mitte", gruppe="kreis 10")]
    assert paare_mitte(punkte, 0, TOL) == []
    ist = plan(punkte)
    assert not [a for a in ist if a.art in ("symmetrie", "paarabstand")]
    gleich(ist, [Auftrag("ursprung", 0, 0, wert=30), Auftrag("ursprung", 1, 0, wert=30),
                 Auftrag("ausrichtung", 0, 1), Auftrag("ausrichtung", 1, 1)])


def test_paare_mitte_bedingungen():
    # andere Achse verschieden, Koordinate nicht entgegengesetzt gleich, Bezug nicht mitte: kein Paar
    assert paare_mitte([punkt(-10, 1, "mitte"), punkt(10, 2, "mitte")], 0, TOL) == []
    assert paare_mitte([punkt(-10, 1, "mitte"), punkt(12, 1, "mitte")], 0, TOL) == []
    assert paare_mitte([punkt(-10, 1, "mitte"), punkt(10, 1, "ursprung")], 0, TOL) == []
    assert paare_mitte([punkt(-10, 1, "mitte"), punkt(10, 1, "mitte")], 0, TOL) == [(0, 1)]
    # Toleranz
    assert paare_mitte([punkt(-10, 1, "mitte"), punkt(10.0005, 1.0005, "mitte")], 0, TOL) == [(0, 1)]


def test_paare_mitte_nur_mit_beiden_achsen():
    # Ein Kennpunkt nur einer Achse (Rechteckmitte in u, Seite in v) bildet kein Paar (Review Task 3)
    halb = Kennpunkt(uv=(-10, 1), achsen=(0,), bezug={0: "mitte", 1: "ursprung"}, gruppe=LOCH)
    assert paare_mitte([halb, punkt(10, 1, "mitte")], 0, TOL) == []
    assert paare_mitte([punkt(10, 1, "mitte"), halb], 0, TOL) == []


def test_ursprung_beide_null_ist_deckung():
    ist = plan([punkt(0, 0)])
    assert ist == [Auftrag("deckung", 0, 0)]
    # mit Rand auf einer Achse keine Deckung
    ist = plan([punkt(0, 0, "-rand")], {(0, 0): -50.0})
    gleich(ist, [Auftrag("bezug", 0, 0, bezug="-rand", wert=50), Auftrag("ausrichtung", 0, 1)])


def test_ursprung_lage_und_ausrichtung():
    ist = plan([punkt(12, 0)])
    gleich(ist, [Auftrag("ursprung", 0, 0, wert=12), Auftrag("ausrichtung", 0, 1)])
    ist = plan([punkt(-12, 7)])
    gleich(ist, [Auftrag("ursprung", 0, 0, wert=12), Auftrag("ursprung", 0, 1, wert=7)])


def test_flaechenbezug_traegt_spec_wert():
    flaeche = {"flaeche": "+x"}
    ist = plan([punkt(5, 3, flaeche)], {(0, 0): 20.0})
    gleich(ist, [Auftrag("bezug", 0, 0, bezug=flaeche, wert=15), Auftrag("ursprung", 0, 1, wert=3)])


def test_kennpunkt_vorgaben():
    k = Kennpunkt(uv=(1.0, 2.0))
    assert k.achsen == (0, 1)
    assert k.bezug == {0: "ursprung", 1: "ursprung"}
    assert k.pfad == "" and k.roh == (None, None) and k.gruppe == ""
    # Vorgaben sind je Instanz eigen
    k.bezug[0] = "mitte"
    assert Kennpunkt(uv=(0.0, 0.0)).bezug[0] == "ursprung"


def test_nur_eine_achse():
    k = Kennpunkt(uv=(4.0, 9.0), achsen=(0,))
    assert plan([k]) == [Auftrag("ursprung", 0, 0, wert=4)]


@pytest.mark.parametrize("mitte, groesse, bezug, lage, soll", [
    (0, 100, "mitte", None, 0),
    (50, 100, "ursprung", None, 0),    # linke Seite auf 0
    (0, 100, "ursprung", None, 0),     # Mitte auf 0
    (-60, 20, "-rand", -80, -70),
    (-60, 20, "+rand", 80, -50),
    (-60, 20, "ursprung", None, -50),  # dem Ursprung nächste Seite
    (30, 20, {"flaeche": "+x"}, 80, 40),
    (30, 20, {"flaeche": "-x"}, -80, 20),
])
def test_rechteck_kennkoordinate(mitte, groesse, bezug, lage, soll):
    assert rechteck_kennkoordinate(mitte, groesse, bezug, lage) == pytest.approx(soll)


def test_rechteck_kennkoordinate_mitte_mit_versatz():
    assert rechteck_kennkoordinate(15, 40, "mitte", None) == pytest.approx(15)
