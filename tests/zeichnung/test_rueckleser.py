"""Reine Teile des Rücklesers (Plan Z1.4 Task 4b): Toleranz, Maßart, Instanzzahl, Blattformat, Sichtbarkeit."""

from swki.zeichnung import rueckleser as rl
from swki.zeichnung.anforderungen_setzen import Kante
from swki.zeichnung.ist import IstToleranz


def _gerade(a, e):
    return Kante(None, a, e, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def _kreis(m, r):
    return Kante(None, (m[0] + r, m[1]), (m[0] + r, m[1]), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), kreis=(m, r))


# --- Toleranz ---------------------------------------------------------------------------------------------------------

def test_toleranz_symmetrisch_mit_vorzeichen():
    """Review Task 3 (M2): ±0,02 ergibt oben 0,02, unten −0,02 in mm."""
    t = rl.toleranz(4, -2e-05, 2e-05, "", "")
    assert t.typ == "symmetrisch" and abs(t.oben - 0.02) < 1e-9 and abs(t.unten + 0.02) < 1e-9


def test_toleranz_arten():
    assert rl.toleranz(0, 0.0, 0.0, "", "") == IstToleranz("keine", None, None, None)
    assert rl.toleranz(2, -5e-05, 1e-04, "", "").typ == "bilateral"
    assert rl.toleranz(3, -5e-05, 1e-04, "", "").typ == "grenz"
    bohrung = rl.toleranz(7, 0.0, 2.1e-05, "H7", "")
    assert bohrung.typ == "passung" and bohrung.passung == "H7"
    assert rl.toleranz(7, 2e-06, 1.8e-05, "", "k6").passung == "k6"
    assert rl.toleranz(8, 0.0, 2.1e-05, "H7", "").passung == "H7"


def test_toleranz_unbekannt_nie_keine():
    """Ein unbekannter swTolType darf nie „keine“ werden (sonst ginge Z-TOL-3 verloren)."""
    for typ in (1, 5, 6, 9, 10, 11, 99):
        t = rl.toleranz(typ, 0.0, 0.0, "", "")
        assert t.typ not in ("keine", "bilateral", "grenz", "symmetrisch", "passung") and str(typ) in t.typ


def test_passung_ohne_text_bleibt_passung():
    assert rl.toleranz(7, 0.0, 0.0, "", "").passung is None


# --- Maßart -----------------------------------------------------------------------------------------------------------

def test_massart():
    assert rl.massart(2, "", " 200,00 ") == "laenge"
    assert rl.massart(11, "4 × ", " 4 × 30,00 (= 120) ") == "laenge"
    assert rl.massart(2, "<MOD-DIAM>", " <MOD-DIAM>50,00 ") == "durchmesser"   # Längsschnitt der Buchse
    assert rl.massart(6, "", " <MOD-DIAM>8,00 ") == "durchmesser"
    assert rl.massart(15, "", "") == "durchmesser"
    assert rl.massart(5, "R", " R4,00 ") == "radius"
    assert rl.massart(14, "", "") == "radius"
    assert rl.massart(3, "", " 90° ") == "winkel"
    assert rl.massart(1, "", "") is None and rl.massart(10, "", "") is None


def test_praefix_mit_durchmesser_aus_der_anzeige():
    """Ein Ø-Maß zeigt das Zeichen auch ohne Präfixtext (Z-DRE-1 prüft, was das Rücklesen sieht)."""
    assert rl.praefix("durchmesser", "", " <MOD-DIAM>8,00 ") == "Ø"
    assert rl.praefix("durchmesser", "<MOD-DIAM>", " <MOD-DIAM>50,00 ") == "<MOD-DIAM>"
    assert rl.praefix("durchmesser", "2 × ", " 2 × Ø8,00 ") == "2 × Ø"
    assert rl.praefix("durchmesser", "", " 8,00 ") == ""
    assert rl.praefix("laenge", "4 × ", " 4 × 30,00 ") == "4 × "


# --- Instanzzahl, Blatt, Rauheitstext ---------------------------------------------------------------------------------

def test_anzahl_ueber_dem_rahmen():
    assert rl.anzahl("2 ×") == 2 and rl.anzahl(" 12 × ") == 12 and rl.anzahl("3x") == 3
    assert rl.anzahl("") is None and rl.anzahl(None) is None and rl.anzahl("ALLE") is None


def test_format_und_massstab():
    assert rl.format_name(420.0, 297.0) == "A3quer" and rl.format_name(210.0, 297.0) == "A4"
    assert rl.format_name(594.0, 420.0) == "594×420"
    assert rl.massstab_text(1.0, 2.0) == "1:2" and rl.massstab_text(2.0, 1.0) == "2:1"
    assert rl.massstab_text(1.0, 2.5) == "1:2,5"


def test_rauheitstext_feld_c_weicht_ab():
    """Nachtrag: Text in Feld c (Fertigungsverfahren) statt Feld a ist „weicht ab“."""
    assert rl.rauheitstext("Ra 0,8", "") == "Ra 0,8"
    assert rl.rauheitstext("Ra 0,8", "geschliffen") == "Ra 0,8 (Feld c: geschliffen)"
    assert rl.rauheitstext("", "Ra 0,8") == "(Feld c: Ra 0,8)"


# --- Sichtbarkeit (`verdeckt`) ---------------------------------------------------------------------------------------

def test_verdeckt_beide_punkte_auf_kanten():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0)), _gerade((50.0, 0.0), (50.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((50.0, 21.0), (50.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (50.0, 20.0)], "h", linien, kanten, [], 1.0) is False


def test_verdeckt_punkt_ohne_kante():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((30.0, 21.0), (30.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (30.0, 20.0)], "h", linien, kanten, [], 1.0) is True


def test_verdeckt_mittellinie_zaehlt():
    kanten = [_gerade((0.0, 0.0), (0.0, 20.0))]
    mitte = [((30.0, -3.0), (30.0, 23.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((30.0, 11.0), (30.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (30.0, 10.0)], "h", linien, kanten, mitte, 0.5) is False


def test_verdeckt_virtuelle_fasenecke():
    """Dieselbe Streckenregel wie `kante_am_punkt`: 0,5 mm über das Kantenende hinaus (Fase 0,5 × 45°, 1:1) ist
    sichtbar; mit nur 0,1 mm Toleranz entstünde ein falscher Mangel „ohne sichtbaren Bezug“."""
    kanten = [_gerade((0.0, 0.0), (0.0, 19.5)), _gerade((40.0, 0.0), (40.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((40.0, 21.0), (40.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (40.0, 20.0)], "h", linien, kanten, [], 1.0) is False
    assert rl.verdeckt([(0.0, 21.5), (40.0, 20.0)], "h", linien, kanten, [], 1.0) is True


def _tasche_r4():
    """Live 28.11. (SpannplatteZ, Einzelheit Z 1:1): Ecke der Tasche 50 × 30 mit R4 – gerade Kanten enden 4 mm vor der
    gedachten scharfen Ecke (306,88 | 209,44), der Bogen verbindet ihre Enden."""
    return [_gerade((306.88, 235.44), (306.88, 213.44)), _gerade((310.88, 209.44), (352.88, 209.44)),
            Kante(None, (306.88, 213.44), (310.88, 209.44), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  kreis=((310.88, 213.44), 4.0)),
            _gerade((356.88, 213.44), (356.88, 235.44)),
            Kante(None, (352.88, 209.44), (356.88, 213.44), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                  kreis=((352.88, 213.44), 4.0))]


def test_verdeckt_gedachte_scharfe_ecke():
    """Maß 50 der gerundeten Tasche setzt an der gedachten scharfen Ecke an: Schnittpunkt der Geraden zweier
    sichtbarer Kanten, deren Enden ein sichtbarer Bogen (oder eine Fasenkante) verbindet – sichtbarer Bezug
    (wie `mittellinien.ohne_kante`, „gedachte scharfe Ecke“, Live 19.11.)."""
    kanten = _tasche_r4()
    linien = [((306.88, 208.44), (306.88, 193.44)), ((356.88, 208.44), (356.88, 193.44))]
    assert rl.verdeckt([(306.88, 209.44), (356.88, 209.44)], "h", linien, kanten, [], 1.0) is False
    assert rl.virtuelle_ecke((306.88, 209.44), kanten) and rl.virtuelle_ecke((356.88, 209.44), kanten)


def test_keine_gedachte_ecke_ohne_verbindung():
    """Zwei Geraden schneiden sich im Punkt, aber nichts Sichtbares verbindet ihre Enden: kein Bezug (sonst wäre
    jeder Schnittpunkt zweier Kantenverlängerungen sichtbar)."""
    kanten = [k for k in _tasche_r4() if not k.kreis]
    assert not rl.virtuelle_ecke((306.88, 209.44), kanten)
    linien = [((306.88, 208.44), (306.88, 193.44)), ((356.88, 208.44), (356.88, 193.44))]
    assert rl.verdeckt([(306.88, 209.44), (356.88, 209.44)], "h", linien, kanten, [], 1.0) is True


def test_verdeckt_kreismitte():
    kanten = [_kreis((10.0, 10.0), 4.0), _gerade((0.0, 0.0), (0.0, 20.0))]
    linien = [((0.0, 21.0), (0.0, 30.0)), ((10.0, 15.0), (10.0, 30.0))]
    assert rl.verdeckt([(0.0, 20.0), (10.0, 10.0)], "h", linien, kanten, [], 1.0) is False
