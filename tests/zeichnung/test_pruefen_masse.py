"""Prüfungen der Maße und Ansichten (Plan Z1.4 Task 2, Negativfälle Design §10)."""

from dataclasses import replace

from swki.zeichnung.ist import IstAngabe, IstAnsicht, IstMass, IstToleranz
from swki.zeichnung.massplan import Mass
from swki.zeichnung.pruefen import (IST_ART, VORZUGSMASSSTAEBE, pruefe_ansichten, pruefe_drehteil, pruefe_gewinde,
                                    pruefe_ueberbestimmt, pruefe_vollstaendig, zuordnen)
from swki.zeichnung.regeln import lade_regeln
from tests.zeichnung.ist_bau import ideal_ist, plan_buchse_z, plan_spannplatte_z

REGELN = lade_regeln()
KEINE = IstToleranz("keine", None, None, None)


def _regeln_der(pruefung: dict) -> set[str]:
    return {m["regel"] for m in pruefung["maengel"]}


def _ohne(ist, **kw):
    """Ist ohne die Maße, deren Felder `kw` entsprechen."""
    return replace(ist, masse=tuple(m for m in ist.masse if not all(getattr(m, k) == v for k, v in kw.items())))


def _mass(name, wert, ansicht="haupt", punkte=((0.0, 0.0), (50.0, 0.0)), richtung="h", klammer=False, **kw):
    return IstMass(name, ansicht, "laenge", wert, "", "", klammer, KEINE, richtung, punkte, kw.pop("verdeckt", False))


def _ist_mit(masse=(), ansichten=(), angaben=()):
    from swki.zeichnung.ist import Ist

    return Ist("A3", "1:1", tuple(ansichten), tuple(masse), tuple(angaben))


# --- Vollständigkeit ----------------------------------------------------------------------------------------------------

def test_form_der_pruefung():
    p = pruefe_vollstaendig(ideal_ist(plan_spannplatte_z()), plan_spannplatte_z(), REGELN)
    assert {"id", "regeln", "ok", "maengel"} <= set(p) and p["id"] == "vollstaendig" and p["maengel"] == []


def test_ideal_vollstaendig():
    plan = plan_spannplatte_z()
    assert pruefe_vollstaendig(ideal_ist(plan), plan, REGELN)["ok"] is True
    plan = plan_buchse_z()
    assert pruefe_vollstaendig(ideal_ist(plan), plan, REGELN)["ok"] is True


def test_fehlendes_mass():
    plan = plan_spannplatte_z()
    p = pruefe_vollstaendig(_ohne(ideal_ist(plan), name="D1@f1_skizze"), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-1"}
    assert "200" in p["maengel"][0]["text"] and p["maengel"][0]["text"].startswith("fehlt:")
    assert p["maengel"][0]["merkmal"] == "f1"


def test_fehlender_durchmesser_mit_zeichen_im_text():
    plan = plan_buchse_z()
    p = pruefe_vollstaendig(_ohne(ideal_ist(plan), art="durchmesser", wert=32.0), plan, REGELN)
    assert p["ok"] is False and "Ø32" in p["maengel"][0]["text"]


def test_doppeltes_mass():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    erstes = next(m for m in ist.masse if m.name == "D1@f1_skizze")
    ist = replace(ist, masse=ist.masse + (replace(erstes, name="D9", ansicht="seite"),))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-2"} and "200" in p["maengel"][0]["text"]
    assert p["maengel"][0]["text"].startswith("doppelt:")


def test_gleicher_wert_zwei_merkmale():
    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a"), Mass("b", "modell", "lage", 20.0, "f2", name="b")]
    ist = ideal_ist(plan)
    assert len(ist.masse) == 2 and pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True
    p = pruefe_vollstaendig(replace(ist, masse=ist.masse[:1]), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-1"}


def test_spannplatte_vier_mal_20():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    zwanzig = [m for m in ist.masse if m.wert == 20.0]
    assert len(zwanzig) >= 3
    p = pruefe_vollstaendig(replace(ist, masse=tuple(m for m in ist.masse if m is not zwanzig[0])), plan, REGELN)
    assert [m["regel"] for m in p["maengel"]] == ["Z-VOLL-1"]


def test_klammermass_zaehlt_nicht():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    ist = replace(ist, masse=tuple(replace(m, klammer=True) if m.name == "D1@f1_skizze" else m for m in ist.masse))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False and "200" in p["maengel"][0]["text"]


def test_zusatz_fehlt_teilung():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    ist = replace(ist, masse=tuple(replace(m, praefix="", suffix="") if m.name == "D3@m1" else m for m in ist.masse))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False and [m["regel"] for m in p["maengel"]] == ["Z-VOLL-1"]
    assert p["maengel"][0]["text"] == "Zusatz fehlt: 4 × 30 (= 120)" and p["maengel"][0]["merkmal"] == "m1"


def test_zusatz_fehlt_fase():
    plan = plan_buchse_z()
    ist = ideal_ist(plan)
    ist = replace(ist, masse=tuple(replace(m, suffix="") if m.name == "D1@f2" else m for m in ist.masse))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False and p["maengel"][0]["text"].startswith("Zusatz fehlt:") and "× 45°" in p["maengel"][0]["text"]


def test_zusatz_leerraum_normalisiert():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    ist = replace(ist, masse=tuple(replace(m, praefix=" 4  ×", suffix="(=  120)") if m.name == "D3@m1" else m
                                   for m in ist.masse))
    assert pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True


def test_zusatz_bevorzugt_passenden_kandidaten():
    """Zwei Plan-Maße gleichen Werts, nur eines mit Zusatz: der Zusatz geht an das richtige Ist-Maß."""
    plan = [Mass("a", "modell", "abstand", 30.0, "m1", name="a", praefix="4 × ", suffix=" (= 120)"),
            Mass("b", "modell", "laenge", 30.0, "f2", name="b")]
    ist = ideal_ist(plan)
    ist = replace(ist, masse=ist.masse[::-1])
    assert pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True
    z = zuordnen(ist, plan)
    assert z["a"].suffix.strip() == "(= 120)" and z["b"].suffix == ""


def test_zuordnen_je_plan_id():
    plan = plan_spannplatte_z()
    z = zuordnen(ideal_ist(plan), plan)
    masse = [m for m in plan if m.quelle == "modell"]
    assert set(z) >= {m.id for m in masse} and all(z[m.id] is not None for m in masse)
    assert {z[m.id].wert for m in masse} == {m.wert for m in masse}
    ohne = zuordnen(_ohne(ideal_ist(plan), name="D1@f1_skizze"), plan)
    assert ohne["D1@f1_skizze"] is None


def test_angabe_fehlt():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    p = pruefe_vollstaendig(replace(ist, angaben=ist.angaben[1:]), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-1"} and "M6" in p["maengel"][0]["text"]


def test_angabe_text_normalisiert_und_doppelt():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    erste = ist.angaben[0]
    # Runde E: Leerraum (Umbruch als „ – “, doppelte Leerzeichen) ist gleich; der Umbruch ist ein Trenner, kein
    # Leerzeichen (früher replace("\n", " ") – das schrieb nur die alte Normalisierung fest). Ein Zusatz dahinter ist
    # seit dem Gesamtreview (M4) ein Unterschied: test_angabe_rest_hinter_dem_plantext_weicht_ab
    umbruch = replace(erste, text=erste.text.replace("\n", "  –  ").replace(" × ", "  ×  "))
    assert pruefe_vollstaendig(replace(ist, angaben=(umbruch,) + ist.angaben[1:]), plan, REGELN)["ok"] is True
    p = pruefe_vollstaendig(replace(ist, angaben=ist.angaben + (erste,)), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-2"}


def test_unbekannte_art_ist_mangel():
    plan = [Mass("x", "modell", "seltsam", 5.0, "f1", name="x")]
    p = pruefe_vollstaendig(ideal_ist([]), plan, REGELN)
    assert p["ok"] is False and p["maengel"][0]["regel"] == "Z-VOLL-1"
    assert p["maengel"][0]["text"] == "Art seltsam nicht prüfbar"


def test_art_tabelle_deckt_beide_referenzen():
    for plan in (plan_spannplatte_z(), plan_buchse_z()):
        assert {m.art for m in plan if m.quelle in ("modell", "neu")} <= set(IST_ART)


def test_ueberzaehliges_mass_ohne_plan():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    extra = _mass("X1", 37.0, ansicht="seite")
    p = pruefe_vollstaendig(replace(ist, masse=ist.masse + (extra,)), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-2"} and "37" in p["maengel"][0]["text"]


# --- Überbestimmt -------------------------------------------------------------------------------------------------------

def _kette(klammer=False):
    return _ist_mit([_mass("a", 50.0, punkte=((0.0, 5.0), (50.0, 5.0))), _mass("b", 30.0, punkte=((50.0, 9.0), (80.0, 9.0))),
                     _mass("c", 80.0, punkte=((0.0, 1.0), (80.0, 1.0)), klammer=klammer)])


def test_geschlossene_kette():
    p = pruefe_ueberbestimmt(_kette(), REGELN)
    assert p["id"] == "ueberbestimmt" and p["ok"] is False and _regeln_der(p) == {"Z-UEB-1"}
    assert "haupt" in p["maengel"][0]["text"]


def test_hilfsmass_in_klammern():
    assert pruefe_ueberbestimmt(_kette(klammer=True), REGELN)["ok"] is True


def test_kette_nach_ansicht_und_richtung_getrennt():
    ist = _ist_mit([_mass("a", 50.0, punkte=((0.0, 0.0), (50.0, 0.0))),
                    _mass("b", 30.0, punkte=((50.0, 0.0), (80.0, 0.0)), ansicht="seite"),
                    _mass("c", 80.0, punkte=((0.0, 0.0), (80.0, 0.0)), ansicht="oben")])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is True
    senkrecht = _ist_mit([_mass("a", 50.0), _mass("b", 30.0, punkte=((0.0, 50.0), (0.0, 80.0)), richtung="v")])
    assert pruefe_ueberbestimmt(senkrecht, REGELN)["ok"] is True


def test_senkrechte_kette_nutzt_y():
    ist = _ist_mit([_mass("a", 50.0, punkte=((9.0, 0.0), (9.0, 50.0)), richtung="v"),
                    _mass("b", 30.0, punkte=((3.0, 50.0), (3.0, 80.0)), richtung="v"),
                    _mass("c", 80.0, punkte=((1.0, 0.0), (1.0, 80.0)), richtung="v")])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is False


def test_rundung_auf_005():
    ist = _ist_mit([_mass("a", 50.0, punkte=((0.0, 0.0), (50.0, 0.0))),
                    _mass("b", 30.0, punkte=((50.01, 0.0), (80.0, 0.0))),
                    _mass("c", 80.0, punkte=((0.01, 0.0), (80.02, 0.0)))])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is False


def test_bezugsbemassung_ideal_ok():
    for plan in (plan_spannplatte_z(), plan_buchse_z()):
        assert pruefe_ueberbestimmt(ideal_ist(plan), REGELN)["ok"] is True


def test_ueberbestimmt_ohne_punkte_nicht_pruefbar():
    ist = _ist_mit([_mass("a", 50.0, punkte=None)])
    p = pruefe_ueberbestimmt(ist, REGELN)
    assert p["ok"] is None and "1" in p["hinweis"]


# --- Ansichten ----------------------------------------------------------------------------------------------------------

def test_mass_an_verdeckter_kante():
    ist = _ist_mit([_mass("a", 50.0, verdeckt=True)], [IstAnsicht("haupt", None, "ansicht", "1:1", None)])
    p = pruefe_ansichten(ist, REGELN)
    assert p["id"] == "ansichten" and p["ok"] is False and _regeln_der(p) == {"Z-ANS-1"}


def test_schnitt_ohne_bezeichnung():
    for beschriftung in (None, "  "):
        ist = _ist_mit(ansichten=[IstAnsicht("Schnitt", None, "schnitt", "1:1", beschriftung)])
        p = pruefe_ansichten(ist, REGELN)
        assert p["ok"] is False and _regeln_der(p) == {"Z-ANS-2"}


def test_einzelheit_massstab_3zu1():
    ist = _ist_mit(ansichten=[IstAnsicht("Einzelheit", None, "einzelheit", "3:1", "B")])
    p = pruefe_ansichten(ist, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-ANS-3"} and "3:1" in p["maengel"][0]["text"]


def test_einzelheit_ohne_massstab():
    ist = _ist_mit(ansichten=[IstAnsicht("Einzelheit", None, "einzelheit", "", "B")])
    assert _regeln_der(pruefe_ansichten(ist, REGELN)) == {"Z-ANS-3"}


def test_einzelheit_vorzugsreihe_ok():
    assert "2:1" in VORZUGSMASSSTAEBE and "1:1" in VORZUGSMASSSTAEBE and "3:1" not in VORZUGSMASSSTAEBE
    ist = _ist_mit(ansichten=[IstAnsicht("Einzelheit", None, "einzelheit", "2 : 1", "B"),
                              IstAnsicht("Schnitt", None, "schnitt", "1:1", "A-A")])
    assert pruefe_ansichten(ist, REGELN)["ok"] is True


def test_verdeckt_unbekannt_ist_nicht_ok():
    ist = _ist_mit([_mass("a", 50.0, verdeckt=None), _mass("b", 30.0, verdeckt=None)])
    p = pruefe_ansichten(ist, REGELN)
    assert p["ok"] is None and "2" in p["hinweis"]


def test_verdeckt_unbekannt_mit_hartem_mangel_bleibt_false():
    ist = _ist_mit([_mass("a", 50.0, verdeckt=None)], [IstAnsicht("Schnitt", None, "schnitt", "1:1", None)])
    assert pruefe_ansichten(ist, REGELN)["ok"] is False


def test_nichtlineare_masse_ohne_verdeckt_sind_kein_befund():
    plan = plan_buchse_z()
    assert pruefe_ansichten(ideal_ist(plan), REGELN)["ok"] is True


# --- Drehteil -----------------------------------------------------------------------------------------------------------

def test_durchmesser_ohne_zeichen():
    plan = plan_buchse_z()
    ist = ideal_ist(plan)
    assert pruefe_drehteil(ist, plan, REGELN)["ok"] is True
    ziel = next(m for m in ist.masse if m.art == "durchmesser")
    ist = replace(ist, masse=tuple(replace(m, praefix="") if m is ziel else m for m in ist.masse))
    p = pruefe_drehteil(ist, plan, REGELN)
    assert p["id"] == "drehteil" and p["ok"] is False and _regeln_der(p) == {"Z-DRE-1"}
    assert "Ø" in p["maengel"][0]["text"]


def test_kein_drehteil():
    plan = plan_spannplatte_z()
    p = pruefe_drehteil(ideal_ist(plan), plan, REGELN)
    assert p["ok"] is None and p["hinweis"] == "kein Drehteil"


# --- Gewinde ------------------------------------------------------------------------------------------------------------

def test_gewinde_ideal_ok():
    plan = plan_spannplatte_z()
    assert pruefe_gewinde(ideal_ist(plan), plan, REGELN)["ok"] is True


def test_gewinde_ohne_tiefe():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    ist = replace(ist, angaben=tuple(replace(a, text=a.text.replace(" tief", "")) if "M6" in a.text else a
                                     for a in ist.angaben))
    p = pruefe_gewinde(ist, plan, REGELN)
    assert p["id"] == "gewinde" and p["ok"] is False and _regeln_der(p) == {"Z-GEW-1"} and "tief" in p["maengel"][0]["text"]


def test_gewinde_notiz_fehlt():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    p = pruefe_gewinde(replace(ist, angaben=tuple(a for a in ist.angaben if "M6" not in a.text)), plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-GEW-1"} and "M6" in p["maengel"][0]["text"]


def test_gewinde_ohne_gewinde_im_plan():
    plan = plan_buchse_z()
    p = pruefe_gewinde(ideal_ist(plan), plan, REGELN)
    assert p["ok"] is None and p["hinweis"] == "kein Gewinde"


# --- Nachbesserung Review (I-1, I-2, M-1, M-2, M-4, M-5, Ⓔ-Tag) ----------------------------------------------------------

def test_gleicher_wert_zwei_merkmale_keine_kette():
    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a"), Mass("b", "modell", "lage", 20.0, "f2", name="b")]
    ist = _ist_mit([_mass("a", 20.0, punkte=((0.0, 10.0), (20.0, 10.0))),
                    _mass("b", 20.0, punkte=((0.0, 40.0), (20.0, 40.0)))])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is True
    assert pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True


def test_spannplatte_ideal_alle_in_einer_ansicht():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    assert {m.ansicht for m in ist.masse} == {"haupt"}
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is True


def test_ueberbestimmt_hinweis_nennt_zufall():
    assert "zusammenfallende" in pruefe_ueberbestimmt(_kette(klammer=True), REGELN)["hinweis"]


def _toleriert(name, wert, tol):
    return replace(_mass(name, wert), toleranz=tol)


def test_zuordnen_toleranz_hat_vorrang():
    from swki.zeichnung.toleranzangaben import Toleranz

    a = Mass("a", "modell", "laenge", 20.0, "f1", name="a", toleranz=Toleranz(None, 0.02, -0.02, False))
    b = Mass("b", "modell", "laenge", 20.0, "f2", name="b")
    mit = _toleriert("x", 20.0, IstToleranz("symmetrisch", None, 0.02, -0.02))
    ohne = _mass("y", 20.0)
    for ist_masse in ((mit, ohne), (ohne, mit)):
        z = zuordnen(_ist_mit(ist_masse), [a, b])
        assert z["a"] is mit and z["b"] is ohne
        z = zuordnen(_ist_mit(ist_masse), [b, a])
        assert z["a"] is mit and z["b"] is ohne


def test_zuordnen_passung():
    from swki.zeichnung.toleranzangaben import Toleranz

    a = Mass("a", "neu", "durchmesser", 20.0, "f1", toleranz=Toleranz("H7", None, None, True))
    b = Mass("b", "neu", "durchmesser", 20.0, "f2", toleranz=Toleranz("k6", None, None, True))
    h7 = replace(_mass("h", 20.0), art="durchmesser", toleranz=IstToleranz("passung", "H7", None, None))
    k6 = replace(_mass("k", 20.0), art="durchmesser", toleranz=IstToleranz("passung", "k6", None, None))
    z = zuordnen(_ist_mit((h7, k6)), [b, a])
    assert z["a"] is h7 and z["b"] is k6


def test_werte_mit_toleranz_nicht_ueber_rundungsgrenze():
    plan = [Mass("a", "modell", "laenge", 12.345, "f1", name="a")]
    for wert in (12.345, 12.345 + 1e-9, 12.349):
        assert pruefe_vollstaendig(_ist_mit([_mass("x", wert)]), plan, REGELN)["ok"] is True
    assert pruefe_vollstaendig(_ist_mit([_mass("x", 12.36)]), plan, REGELN)["ok"] is False


def test_knoten_clustern_statt_runden():
    ist = _ist_mit([_mass("a", 50.0, punkte=((0.0, 0.0), (0.0249, 0.0))),
                    _mass("b", 50.0, punkte=((0.0249, 0.0), (0.0498, 0.0))),
                    _mass("c", 50.0, punkte=((0.0, 0.0), (0.0498, 0.0)))])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is True      # alle in einem Cluster: keine Kante
    ist = _ist_mit([_mass("a", 50.0, punkte=((0.0, 0.0), (50.0, 0.0))),
                    _mass("b", 30.0, punkte=((50.04, 0.0), (80.0, 0.0))),
                    _mass("c", 80.0, punkte=((0.04, 0.0), (80.03, 0.0)))])
    assert pruefe_ueberbestimmt(ist, REGELN)["ok"] is False


def test_unbekannte_quelle_genannt():
    p = pruefe_vollstaendig(ideal_ist([]), [Mass("x", "foo", "laenge", 5.0, "f1")], REGELN)
    assert p["ok"] is False and p["maengel"][0]["text"] == "Quelle foo nicht prüfbar"


def test_angabe_ohne_text_ist_mangel():
    p = pruefe_vollstaendig(ideal_ist([]), [Mass("x:angabe", "angabe", "angabe", 0.0, "g1", text=None)], REGELN)
    assert p["ok"] is False and p["maengel"][0] == {"regel": "Z-VOLL-1", "merkmal": "g1", "text": "Angabe ohne Text: g1"}


def test_zusatz_am_rand_nicht_in_der_mitte():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    ist = replace(ist, masse=tuple(replace(m, praefix="14 × ") if m.name == "D3@m1" else m for m in ist.masse))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False and p["maengel"][0]["text"].startswith("Zusatz fehlt")


def test_huelle_tag_gleich_symbol():
    from swki.zeichnung.pruefen import normtext
    from swki.zeichnung.toleranzangaben import Toleranz

    assert normtext("  Ø  <MOD-EP> ") == "Ø Ⓔ"
    plan = [Mass("a", "neu", "durchmesser", 20.0, "f1", suffix=" Ⓔ", toleranz=Toleranz("H7", None, None, True))]
    ist = replace(_mass("x", 20.0), art="durchmesser", praefix="Ø", suffix=" <MOD-EP>",
                  toleranz=IstToleranz("passung", "H7", None, None))
    assert pruefe_vollstaendig(_ist_mit([ist]), plan, REGELN)["ok"] is True
    notiz = IstAngabe("hinweis", "haupt", "2 × Ø8 H7 <MOD-EP> – 15 tief", None, None, (), "st")
    angabe = Mass("s:angabe", "angabe", "angabe", 0.0, "st", text="2 × Ø8 H7 Ⓔ – 15 tief")
    assert pruefe_vollstaendig(_ist_mit(angaben=[notiz]), [angabe], REGELN)["ok"] is True


# --- Nachbesserung Re-Review ---------------------------------------------------------------------------------------------

def test_zuordnung_unabhaengig_von_reihenfolge():
    import itertools

    a = Mass("a", "modell", "laenge", 20.0, "f1", name="a")
    b = Mass("b", "modell", "laenge", 20.0, "f2", name="b", suffix=" tief")
    x = replace(_mass("x", 20.0), suffix=" tief")
    y = _mass("y", 20.0)
    for plan in itertools.permutations([a, b]):
        for masse in itertools.permutations([x, y]):
            ist = _ist_mit(masse)
            assert pruefe_vollstaendig(ist, list(plan), REGELN)["ok"] is True
            z = zuordnen(ist, list(plan))
            assert z["a"] is y and z["b"] is x


def test_zusatz_exakt_leer_nur_zu_leer():
    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a")]
    p = pruefe_vollstaendig(_ist_mit([replace(_mass("x", 20.0), suffix=" tief")]), plan, REGELN)
    assert p["ok"] is False                      # Ist trägt einen Zusatz, den der Plan nicht kennt


def test_huelle_im_zusatz_wird_ignoriert():
    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a", suffix=" (= 20)")]
    ist = _ist_mit([replace(_mass("x", 20.0), suffix=" (= 20) <MOD-EP>")])
    assert pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True


def test_cluster_complete_linkage():
    from swki.zeichnung.pruefen import _cluster

    assert len(_cluster([0.0, 0.04, 0.08])) == 2
    assert len(_cluster([0.0, 0.03, 0.05])) == 1


import pytest  # noqa: E402


def test_huelle_ohne_passmass_ist_mangel():
    """Ⓔ verschluckt der Zusatzvergleich bewusst; Hülle ohne Passmaß meldet pruefe_toleranzen (Z-TOL-2)."""
    from swki.zeichnung import pruefen

    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a")]
    ist = _ist_mit([replace(_mass("x", 20.0), suffix=" <MOD-EP>")])
    p = pruefen.pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-2"}


# --- Runde D: Umbruch und „ – “ sind gleichwertige Trenner einer Bohrungsangabe -------------------------------------

_UMBRUCH = chr(10)


@pytest.mark.parametrize("ist_text", ["2 × Ø8 H7 <MOD-EP> – 15 tief" + _UMBRUCH + "Fase 0,5 × 45°",
                                      _UMBRUCH.join(["2 × Ø8 H7 <MOD-EP>", "15 tief", "Fase 0,5 × 45°"]),
                                      (chr(13) + _UMBRUCH).join(["2 × Ø8 H7 <MOD-EP>", "15 tief", "Fase 0,5 × 45°"])])
def test_angabe_umbruch_statt_strich_gleich(ist_text):
    from swki.zeichnung.pruefen import angabentext

    angabe = Mass("s:angabe", "angabe", "angabe", 0.0, "st", text="2 × Ø8 H7 Ⓔ – 15 tief" + _UMBRUCH + "Fase 0,5 × 45°")
    notiz = IstAngabe("hinweis", "haupt", ist_text, None, None, (), "st")
    assert pruefe_vollstaendig(_ist_mit(angaben=[notiz]), [angabe], REGELN)["ok"] is True
    assert angabentext(ist_text) == angabentext(angabe.text)


def test_angabe_trenner_gleich_inhalt_nicht():
    """Die Form des Trenners zählt nicht, der Inhalt schon."""
    angabe = Mass("s:angabe", "angabe", "angabe", 0.0, "st", text="2 × Ø8 H7 Ⓔ – 15 tief")
    notiz = IstAngabe("hinweis", "haupt", _UMBRUCH.join(["2 × Ø8 H7 <MOD-EP>", "16 tief"]), None, None, (), "st")
    assert pruefe_vollstaendig(_ist_mit(angaben=[notiz]), [angabe], REGELN)["ok"] is False


def test_gewinde_umbrochen_gleich():
    angabe = Mass("g:angabe", "angabe", "angabe", 0.0, "g", text="5 × M6 – 10 tief" + _UMBRUCH + "Senkung Ø6 × 90°")
    notiz = IstAngabe("hinweis", "haupt", _UMBRUCH.join(["5 × M6", "10 tief", "Senkung Ø6 × 90°"]), None, None, (),
                      "g")
    p = pruefe_gewinde(_ist_mit(angaben=[notiz]), [angabe], REGELN)
    assert p["ok"] is True, p


# --- Runde E: Trenner einer Bohrungsangabe -----------------------------------------------------------------------------


def test_angabe_fehlender_trenner_ist_unterschied():
    """Runde E: „2 × Ø8 H7 Ⓔ 15 tief“ (Trenner fehlt) ist nicht „2 × Ø8 H7 Ⓔ – 15 tief“; Umbruch, „ – “, CRLF und ein
    Strich am Zeilenende sind derselbe Trenner."""
    from swki.zeichnung.pruefen import angabentext

    soll = "2 × Ø8 H7 Ⓔ – 15 tief" + _UMBRUCH + "Fase 0,5 × 45°"
    assert angabentext("2 × Ø8 H7 Ⓔ 15 tief" + _UMBRUCH + "Fase 0,5 × 45°") != angabentext(soll)
    for gleich in ("2 × Ø8 H7 Ⓔ –" + _UMBRUCH + "15 tief" + chr(13) + _UMBRUCH + "Fase 0,5 × 45°",
                   "2 × Ø8 H7 Ⓔ – 15 tief – Fase 0,5 × 45°" + _UMBRUCH,
                   "2 × Ø8 H7 Ⓔ" + _UMBRUCH + _UMBRUCH + "15 tief" + _UMBRUCH + " Fase 0,5 × 45°"):
        assert angabentext(gleich) == angabentext(soll), gleich
    angabe = Mass("s:angabe", "angabe", "angabe", 0.0, "st", text=soll)
    notiz = IstAngabe("hinweis", "haupt", "2 × Ø8 H7 <MOD-EP> 15 tief" + _UMBRUCH + "Fase 0,5 × 45°", None, None, (),
                      "st")
    p = pruefe_vollstaendig(_ist_mit(angaben=[notiz]), [angabe], REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-VOLL-1"}


def test_angabe_doppelt_nennt_ersten_abschnitt():
    """Runde E: Z-VOLL-2 „doppelt“ zeigt den ersten Abschnitt des Ist-Texts, auch bei dreizeiliger Form."""
    angabe = Mass("s:angabe", "angabe", "angabe", 0.0, "st", text="2 × Ø8 H7 Ⓔ – 15 tief" + _UMBRUCH + "Fase 0,5 × 45°")
    drei = IstAngabe("hinweis", "haupt", _UMBRUCH.join(["2 × Ø8 H7 <MOD-EP>", "15 tief", "Fase 0,5 × 45°"]), None,
                     None, (), "st")
    p = pruefe_vollstaendig(_ist_mit(angaben=[drei, drei]), [angabe], REGELN)
    assert [m["text"] for m in p["maengel"]] == ["doppelt: Angabe 2 × Ø8 H7 Ⓔ"]


# --- Gesamtreview I3/M4: Bohrungsangaben je Merkmal der Hinweislinie ------------------------------------------------

def _angabe_von(ist, merkmal):
    return next(a for a in ist.angaben if a.art == "hinweis" and a.merkmal == merkmal)


def _ersetze(ist, alt, neu):
    return replace(ist, angaben=tuple(neu if a is alt else a for a in ist.angaben))


def test_ideal_angaben_tragen_merkmal():
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    assert {_angabe_von(ist, mk).merkmal for mk in ("g1", "st")} == {"g1", "st"}


def test_angabe_an_fremder_hinweislinie_fehlt():
    """Folge 1: „2 × Ø8 H7 Ⓔ – 15 tief“ hängt an der M6-Bohrung (g1) – für st fehlt die Angabe, an g1 ist sie
    überzählig; der Text allein reicht nicht."""
    from swki.zeichnung.pruefen import pruefe_toleranzen

    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    st = _angabe_von(ist, "st")
    ist = _ersetze(ist, st, replace(st, merkmal="g1"))
    p = pruefe_vollstaendig(ist, plan, REGELN)
    assert p["ok"] is False
    assert [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-VOLL-1", "st"), ("Z-VOLL-2", "g1")], p["maengel"]
    assert "fehlt" in p["maengel"][0]["text"] and "an g1 statt st" in p["maengel"][1]["text"]
    assert pruefe_toleranzen(ist, plan, REGELN)["ok"] is True


def test_angabe_nur_passung_abweichend_ist_z_tol_1():
    """Folge 2 (bekannt d): H7 → H8 im Hinweis ist eine falsche Passung (Z-TOL-1), kein fehlender Hinweis."""
    from swki.zeichnung.pruefen import pruefe_toleranzen

    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    st = _angabe_von(ist, "st")
    ist = _ersetze(ist, st, replace(st, text=st.text.replace("H7", "H8")))
    assert pruefe_vollstaendig(ist, plan, REGELN)["ok"] is True
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-TOL-1", "st")]
    assert "H8 Ⓔ statt H7 Ⓔ" in p["maengel"][0]["text"]


def test_angabe_huelle_fehlt_ist_z_tol_1():
    from swki.zeichnung.pruefen import pruefe_toleranzen

    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    st = _angabe_von(ist, "st")
    ist = _ersetze(ist, st, replace(st, text=st.text.replace(" Ⓔ", "")))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-TOL-1", "st")] and "H7 statt H7 Ⓔ" in p["maengel"][0]["text"]


def test_angabe_toleranz_ohne_funktion_ist_z_tol_3():
    from swki.zeichnung.pruefen import pruefe_toleranzen

    angabe = Mass("g:angabe", "angabe", "angabe", 0.0, "b1", text="4 × Ø6 – durch")
    notiz = IstAngabe("hinweis", "haupt", "4 × Ø6 H7 – durch", None, None, (), "b1")
    p = pruefe_toleranzen(_ist_mit(angaben=[notiz]), [angabe], REGELN)
    assert [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-TOL-3", "b1")]


def test_angabe_ohne_kante_ist_ruecklesen_unvollstaendig():
    """Passt der Text, fehlt aber die angehängte Kante (kein Merkmal), ist das nie still passend."""
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    st = _angabe_von(ist, "st")
    p = pruefe_vollstaendig(_ersetze(ist, st, replace(st, merkmal=None)), plan, REGELN)
    assert p["ok"] is False and [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-VOLL-1", "st")]
    assert p["maengel"][0]["text"].startswith("RUECKLESEN_UNVOLLSTAENDIG:")


def test_angabe_rest_hinter_dem_plantext_weicht_ab():
    """M4: „… – 15 tief XYZ“ ist nicht „… – 15 tief“."""
    plan = plan_spannplatte_z()
    ist = ideal_ist(plan)
    st = _angabe_von(ist, "st")
    p = pruefe_vollstaendig(_ersetze(ist, st, replace(st, text=st.text + " XYZ")), plan, REGELN)
    assert p["ok"] is False and [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-VOLL-1", "st")]
    assert p["maengel"][0]["text"].startswith("weicht ab:") and "XYZ" in p["maengel"][0]["text"]


def test_gewinde_nimmt_die_notiz_des_merkmals():
    """Eine freie Notiz „5 × M6 – 10 tief“ ohne Merkmal deckt nicht die Notiz am Gewinde, der „tief“ fehlt."""
    angabe = Mass("g:angabe", "angabe", "angabe", 0.0, "g1", text="5 × M6 – 10 tief")
    frei = IstAngabe("hinweis", "haupt", "5 × M6 – 10 tief", None, None, ())
    am_gewinde = IstAngabe("hinweis", "haupt", "5 × M6", None, None, (), "g1")
    p = pruefe_gewinde(_ist_mit(angaben=[frei, am_gewinde]), [angabe], REGELN)
    assert p["ok"] is False and "tief" in p["maengel"][0]["text"]


def test_schnittbezeichnung_doppelt_ist_z_ans_2():
    """Gesamtreview (a): zwei Schnitte mit derselben Bezeichnung sind nicht zu unterscheiden."""
    zwei = [IstAnsicht("Schnittansicht A-A", "haupt", "schnitt", "1:1", "SCHNITT A-A"),
            IstAnsicht("Schnittansicht A-A (2)", "drauf", "schnitt", "1:1", "SCHNITT  A-A")]
    p = pruefe_ansichten(_ist_mit(ansichten=zwei), REGELN)
    assert p["ok"] is False and [m["regel"] for m in p["maengel"]] == ["Z-ANS-2"] and "doppelt" in p["maengel"][0]["text"]
    anders = [zwei[0], replace(zwei[1], beschriftung="SCHNITT B-B")]
    assert not pruefe_ansichten(_ist_mit(ansichten=anders), REGELN)["maengel"]
