"""Prüfungen der Angaben (Toleranzen, Sammelangaben, Schriftfeld, Lesbarkeit) und Gesamturteil (Plan Z1.4 Task 3)."""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from swki.zeichnung import pruefen
from swki.zeichnung.ist import IstAngabe, IstToleranz
from swki.zeichnung.massplan import massplan_meldungen
from swki.zeichnung.pruefen import (bewerte, normtext, pruefe_drehteil, pruefe_lesbarkeit, pruefe_sammelangaben,
                                    pruefe_schriftfeld, pruefe_toleranzen, soll_luecken)
from swki.zeichnung.regeln import lade_regeln
from tests.zeichnung.ist_bau import ideal_ist, plan_buchse_z, plan_spannplatte_z
from tests.zeichnung.test_massplan import REF, _buchse_protokoll, _lade_ref, _spannplatte, _spannplatte_protokoll

REGELN = lade_regeln()
STANDARD = yaml.safe_load((Path(__file__).parents[2] / "config" / "standard.yaml").read_text(encoding="utf-8"))


def _spec_sp():
    return _lade_ref("zeichnung/spannplatte_z.yaml")


def _spec_bu():
    return _lade_ref("zeichnung/buchse_z.yaml")


def _ideal_sp():
    return ideal_ist(plan_spannplatte_z(), spec=_spec_sp())


def _ideal_bu():
    return ideal_ist(plan_buchse_z(), spec=_spec_bu())


def _bewerte(ist, plan, spec, **kw):
    return bewerte(ist, plan, spec, STANDARD, REGELN, **kw)


def _regeln_der(p: dict) -> set[str]:
    return {m["regel"] for m in p["maengel"]}


def _pruefung(urteil: dict, id_: str) -> dict:
    return next(p for p in urteil["pruefungen"] if p["id"] == id_)


def _ersetze_mass(ist, pred, **kw):
    gefunden = False
    masse = []
    for m in ist.masse:
        if not gefunden and pred(m):
            m, gefunden = replace(m, **kw), True
        masse.append(m)
    assert gefunden
    return replace(ist, masse=tuple(masse))


def _ohne_angabe(ist, pred):
    rest = [a for a in ist.angaben if not pred(a)]
    assert len(rest) < len(ist.angaben)
    return replace(ist, angaben=tuple(rest))


def _notizen(ist, *texte):
    """Weitere Notizen, Ankerpunkt im Band über dem Schriftfeld (A3quer, Gesamtreview c)."""
    return replace(ist, angaben=ist.angaben + tuple(IstAngabe("hinweis", "haupt", t, None, None, (), lage=(231.0, 66.0))
                                                    for t in texte))


def _ohne_notiz_mit(ist, teil):
    return _ohne_angabe(ist, lambda a: a.art == "hinweis" and teil in a.text)


# --- Gesamturteil: ideales Ist ---------------------------------------------------------------------------------------

def test_ideal_spannplatte_z_bestanden():
    u = _bewerte(_ideal_sp(), plan_spannplatte_z(), _spec_sp())
    assert u["bestanden"] is True, u["maengel"]
    assert [p["id"] for p in u["pruefungen"]] == ["vollstaendig", "ueberbestimmt", "toleranzen", "sammelangaben",
                                                  "schriftfeld", "ansichten", "lesbarkeit", "gewinde", "drehteil"]
    assert set(u) >= {"bestanden", "pruefungen", "maengel", "meldungen"}


def test_ideal_buchse_z_bestanden():
    u = _bewerte(_ideal_bu(), plan_buchse_z(), _spec_bu())
    assert u["bestanden"] is True, u["maengel"]


def test_ideal_ohne_anforderungen_bestanden():
    """Review Focus 1: alte Spec ohne Anforderungen; Sammelangaben liefert die vier festen Zeilen."""
    from swki.zeichnung.massplan import massplan
    from swki.zeichnung.toleranzangaben import sammelangaben

    spec, protokoll = _spannplatte()
    assert len(sammelangaben(spec)) == 4
    plan = massplan(spec, protokoll)
    u = _bewerte(ideal_ist(plan, spec=spec), plan, spec)
    assert u["bestanden"] is True, u["maengel"]


# --- Toleranzen ------------------------------------------------------------------------------------------------------

def test_falsche_passung():
    plan = plan_buchse_z()
    ist = _ersetze_mass(_ideal_bu(), lambda m: m.art == "durchmesser" and m.toleranz.passung == "H7",
                        toleranz=IstToleranz("passung", "H8", None, None))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-1"}
    assert "H7" in p["maengel"][0]["text"] and "H8" in p["maengel"][0]["text"]


def test_falsche_abmasse_und_toleranz_fehlt():
    plan = plan_spannplatte_z()
    ist = _ersetze_mass(_ideal_sp(), lambda m: m.toleranz.typ == "symmetrisch",
                        toleranz=IstToleranz("symmetrisch", None, 0.05, -0.05))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert _regeln_der(p) == {"Z-TOL-1"} and "0,02" in p["maengel"][0]["text"] and "0,05" in p["maengel"][0]["text"]
    ist = _ersetze_mass(_ideal_sp(), lambda m: m.toleranz.typ == "symmetrisch", toleranz=IstToleranz("keine", None, None, None))
    assert _regeln_der(pruefe_toleranzen(ist, plan, REGELN)) == {"Z-TOL-1"}


def test_huelle_an_nicht_passmass():
    """Review Focus 4: Ⓔ am Abmaß ±0,02 (Parameter A) ist Z-TOL-2, an H7 kein Mangel."""
    plan = plan_spannplatte_z()
    ist = _ersetze_mass(_ideal_sp(), lambda m: m.toleranz.typ == "symmetrisch", suffix=" Ⓔ")
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-2"}
    plan = plan_buchse_z()
    assert pruefe_toleranzen(_ideal_bu(), plan, REGELN)["ok"] is True      # H7 und k6 tragen Ⓔ


def test_huelle_fehlt_an_passmass():
    plan = plan_buchse_z()
    ist = _ersetze_mass(_ideal_bu(), lambda m: m.art == "durchmesser" and m.toleranz.passung == "H7", suffix="")
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-1"} and "Ⓔ" in p["maengel"][0]["text"]


def test_huelle_als_tag_wird_erkannt():
    plan = plan_buchse_z()
    ist = _ersetze_mass(_ideal_bu(), lambda m: m.art == "durchmesser" and m.toleranz.passung == "H7", suffix=" <MOD-EP>")
    assert pruefe_toleranzen(ist, plan, REGELN)["ok"] is True


def test_toleranz_ohne_funktion():
    plan = plan_spannplatte_z()
    ist = _ersetze_mass(_ideal_sp(), lambda m: m.toleranz.typ == "keine" and m.art == "laenge" and m.wert == 200.0,
                        toleranz=IstToleranz("symmetrisch", None, 0.1, -0.1))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-3"}


def test_rauheit_fehlt():
    plan = plan_spannplatte_z()
    ist = _ohne_angabe(_ideal_sp(), lambda a: a.art == "rauheit" and a.text == "Ra 1,6")
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-4"} and "Ra 1,6" in p["maengel"][0]["text"]
    assert p["maengel"][0]["merkmal"] == "t1"


def test_rauheit_falscher_wert():
    plan = plan_spannplatte_z()
    ist = _ideal_sp()
    ist = replace(ist, angaben=tuple(replace(a, text="Ra 3,2") if a.art == "rauheit" and a.text == "Ra 1,6" else a
                                     for a in ist.angaben))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert _regeln_der(p) == {"Z-TOL-4"} and "Ra 3,2" in p["maengel"][0]["text"] and "Ra 1,6" in p["maengel"][0]["text"]


def test_form_lage_falscher_wert():
    plan = plan_spannplatte_z()
    ist = _ideal_sp()
    ist = replace(ist, angaben=tuple(replace(a, wert="0,05") if a.art == "form_lage" and a.wert == "0,02" else a
                                     for a in ist.angaben))
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-5"}
    assert "0,02" in p["maengel"][0]["text"] and "0,05" in p["maengel"][0]["text"]


def test_form_lage_bezug_fehlt():
    plan = plan_spannplatte_z()
    ist = _ideal_sp()
    ist = replace(ist, angaben=tuple(replace(a, bezug=()) if a.art == "form_lage" and a.bezug else a for a in ist.angaben))
    assert _regeln_der(pruefe_toleranzen(ist, plan, REGELN)) == {"Z-TOL-5"}


def test_bezug_fehlt():
    plan = plan_spannplatte_z()
    ist = _ohne_angabe(_ideal_sp(), lambda a: a.art == "bezug" and a.text == "B")
    p = pruefe_toleranzen(ist, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-6"} and "B" in p["maengel"][0]["text"]


def test_angaben_je_merkmal_ohne_merkmal_kein_joker():
    """Abgleich je Merkmal. Eine Angabe ohne Merkmal deckt nichts (Review 4b, I1/I2: kein Joker): der Plan-Eintrag
    fehlt, die Angabe ist überzählig ohne Merkmal – beides harte Mängel der Art."""
    plan = plan_spannplatte_z()
    ideal = _ideal_sp()
    assert all(a.merkmal for a in ideal.angaben if a.art in ("rauheit", "form_lage"))
    ohne = replace(ideal, angaben=tuple(replace(a, merkmal=None) for a in ideal.angaben))
    p = pruefe_toleranzen(ohne, plan, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-TOL-4", "Z-TOL-5", "Z-TOL-6"}
    assert any(m["text"].startswith("fehlt:") for m in p["maengel"])
    assert any(m["text"].startswith("überzählig:") and "ohne Merkmal" in m["text"] for m in p["maengel"])
    # gleiche Rauheit am falschen Merkmal zählt nicht
    vertauscht = replace(ideal, angaben=tuple(replace(a, merkmal="st" if a.art == "rauheit" and a.merkmal == "t1" else a.merkmal)
                                              if a.art == "rauheit" else a for a in ideal.angaben))
    assert _regeln_der(pruefe_toleranzen(vertauscht, plan, REGELN)) == {"Z-TOL-4"}
    # Multimenge je Merkmal: zweimal dieselbe Rauheit an t1 deckt nur den Plan-Eintrag von t1
    doppelt = replace(ideal, angaben=ideal.angaben + (IstAngabe("rauheit", "haupt", "Ra 1,6", None, None, (), "t1"),))
    assert _regeln_der(pruefe_toleranzen(doppelt, plan, REGELN)) == {"Z-TOL-4"}


def test_huelle_ohne_passmass_wie_task2():
    """Gegenstück zum Marker in test_pruefen_masse: der Mangel kommt von pruefe_toleranzen."""
    from swki.zeichnung.massplan import Mass

    plan = [Mass("a", "modell", "laenge", 20.0, "f1", name="a")]
    ist = replace(ideal_ist(plan), masse=tuple(replace(m, suffix=" <MOD-EP>") for m in ideal_ist(plan).masse))
    assert _regeln_der(pruefe_toleranzen(ist, plan, REGELN)) == {"Z-TOL-2"}


# --- Sammelangaben ---------------------------------------------------------------------------------------------------

def test_sammelangaben_ideal_und_fehlend():
    spec = _spec_bu()
    assert pruefe_sammelangaben(_ideal_bu(), spec, REGELN)["ok"] is True
    for teil, regel in (("ISO 2768-1:1989", "Z-SAM-1"), ("ISO 8015", "Z-SAM-2"), ("ISO 13715", "Z-SAM-6"),
                        ("Maßgebend", "Z-SAM-4"), ("einsatzgehärtet", "Z-SAM-5"), ("Halbzeug", "Z-SAM-5"),
                        ("Ra 3,2", "Z-SAM-7")):
        p = pruefe_sammelangaben(_ohne_notiz_mit(_ideal_bu(), teil), spec, REGELN)
        assert p["ok"] is False and regel in _regeln_der(p), teil


@pytest.mark.parametrize("text", ["Allgemeintoleranzen ISO 2768-mK", "Allgemeintoleranzen ISO 2768-1 mK",
                                  "Allgemeintoleranzen 2768 - mK", "Allgemeintoleranzen DIN 7167"])
def test_iso_2768_mk(text):
    p = pruefe_sammelangaben(_notizen(_ideal_bu(), text), _spec_bu(), REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-SAM-3"}


def test_iso_2768_1_m_ist_kein_treffer():
    ist = _notizen(_ideal_bu(), "Allgemeintoleranzen ISO 2768-1:1989 – m")
    assert pruefe_sammelangaben(ist, _spec_bu(), REGELN)["ok"] is True


def test_sammelangaben_ueber_notizgrenzen_kein_treffer():
    """„… 2768-1 m“ und eine Folgenotiz „Kanten …“ ergeben kein „mK“."""
    ist = _notizen(_ideal_bu(), "ISO 2768-1:1989 – m", "Kanten ISO 13715")
    assert _regeln_der(pruefe_sammelangaben(ist, _spec_bu(), REGELN)) == set()


# --- Schriftfeld -----------------------------------------------------------------------------------------------------

def _mit_eig(ist, **kw):
    eig = dict(ist.eigenschaften)
    eig.update(kw)
    return replace(ist, eigenschaften=eig)


def test_schriftfeld_ideal():
    p = pruefe_schriftfeld(_ideal_sp(), STANDARD, REGELN)
    assert p["ok"] is None and p["maengel"] == [] and "Eigentümer" in p["hinweis"]     # bis Z1.5 nur Hinweis


def test_pflichtfeld_fehlt():
    p = pruefe_schriftfeld(_mit_eig(_ideal_sp(), Benennung=""), STANDARD, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-SCH-1"} and "Benennung" in p["maengel"][0]["text"]
    ist = _ideal_sp()
    ist = replace(ist, eigenschaften={k: v for k, v in ist.eigenschaften.items() if k != "DrawnBy"})
    assert pruefe_schriftfeld(ist, STANDARD, REGELN)["ok"] is False


def test_eigentuemer_leer_nur_hinweis():
    u = _bewerte(_ideal_sp(), plan_spannplatte_z(), _spec_sp())
    assert _pruefung(u, "schriftfeld")["ok"] is None and u["bestanden"] is True


def test_freigegeben_gefuellt():
    p = pruefe_schriftfeld(_mit_eig(_ideal_sp(), Freigegeben="Müller"), STANDARD, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-SCH-2"}


def test_massstab_3zu1():
    p = pruefe_schriftfeld(replace(_ideal_sp(), massstab="3:1"), STANDARD, REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-SCH-3"} and "3:1" in p["maengel"][0]["text"]
    assert pruefe_schriftfeld(replace(_ideal_sp(), massstab="1 : 2"), STANDARD, REGELN)["ok"] is None


def test_blatt_nicht_gelesen_ist_nicht_geprueft():
    """Review 4b (M5): den Blattzähler setzt SolidWorks (Systemeigenschaft), der Rückleser liest ihn nicht – fehlt
    die Eigenschaft, ist das Feld nicht geprüft (`ok` None mit Grund), kein erfundener Wert und kein falscher Mangel."""
    ist = _ideal_sp()
    ohne = replace(ist, eigenschaften={k: v for k, v in ist.eigenschaften.items() if k != "Blatt"})
    p = pruefe_schriftfeld(ohne, STANDARD, REGELN)
    assert p["ok"] is None and p["maengel"] == [] and "Blatt" in p["hinweis"]
    leer = replace(ist, eigenschaften={**ist.eigenschaften, "Blatt": " "})
    p = pruefe_schriftfeld(leer, STANDARD, REGELN)
    assert p["ok"] is False and [m["merkmal"] for m in p["maengel"]] == ["Blatt"]


def test_standard_schriftfeld_belegt():
    sf = STANDARD["zeichnung"]["schriftfeld"]
    assert sf == {"eigentuemer": "", "sachnummer": "Zeichnungsnummer", "titel": "Benennung", "ersteller": "DrawnBy",
                  "ausgabedatum": "DrawnDate", "dokumentart": "Dokumentart", "blatt": "Blatt", "freigegeben": "Freigegeben"}


# --- Soll-Lücken -----------------------------------------------------------------------------------------------------

def test_soll_luecke_toleranz():
    spec = _spec_bu()
    spec["toleranzen"]["GIBTSNICHT"] = {"passung": "h9"}
    meldungen = massplan_meldungen(spec, _buchse_protokoll())
    assert any(m.startswith("TOLERANZ_OHNE_MASS: GIBTSNICHT") for m in meldungen)
    u = _bewerte(_ideal_bu(), plan_buchse_z(), spec, meldungen_soll=meldungen)
    assert u["bestanden"] is False
    m = next(m for m in u["maengel"] if m["regel"] == "Z-TOL-1" and "GIBTSNICHT" in m["text"])
    assert m["pruefung"] == "toleranzen"
    assert _pruefung(u, "toleranzen")["ok"] is False


@pytest.mark.parametrize("meldung,pruefung,regel", [
    ("TOLERANZ_MEHRDEUTIG: D1@f1: A, B", "toleranzen", "Z-TOL-1"),
    ("FORM_LAGE_IT_OHNE_TABELLE: f1 ebenheit IT7 – keine ISO-286-Tabelle", "toleranzen", "Z-TOL-1"),
    ("MASS_NICHT_GEPLANT: f1 – Profilelement bogen wird nicht bemaßt", "vollstaendig", "Z-VOLL-1"),
])
def test_soll_luecke_arten(meldung, pruefung, regel):
    assert soll_luecken([meldung]) == [{"pruefung": pruefung, "regel": regel,
                                        "merkmal": meldung.split(": ")[1].split(":")[0].split(" ")[0], "text": meldung}]
    u = _bewerte(_ideal_bu(), plan_buchse_z(), _spec_bu(), meldungen_soll=[meldung])
    assert u["bestanden"] is False and any(m["regel"] == regel and m["pruefung"] == pruefung for m in u["maengel"])


def test_funktion_unbestaetigt_bleibt_hinweis():
    meldung = "FUNKTION_UNBESTAETIGT: st: c_wert"
    assert soll_luecken([meldung]) == []
    u = _bewerte(_ideal_bu(), plan_buchse_z(), _spec_bu(), meldungen_soll=[meldung])
    assert u["bestanden"] is True and meldung in u["meldungen"]


# --- Ansichten, Lesbarkeit, Ø-Tag --------------------------------------------------------------------------------------

def test_verdeckt_unbekannt():
    plan = plan_spannplatte_z()
    ist = _ideal_sp()
    ist = replace(ist, masse=tuple(replace(m, verdeckt=None) for m in ist.masse))
    n = sum(1 for m in ist.masse if m.art == "laenge")
    u = _bewerte(ist, plan, _spec_sp())
    p = _pruefung(u, "ansichten")
    assert p["ok"] is None and str(n) in p["hinweis"]
    assert u["bestanden"] is True


def test_lesbarkeit_ohne_pdf_nicht_geprueft():
    p = pruefe_lesbarkeit(None, "A3quer", REGELN)
    assert p["ok"] is None and p["hinweis"]


def test_lesbarkeit_ist_hinweis(monkeypatch, tmp_path):
    from swki.zeichnung.lesbarkeit import Befund

    ort = []
    monkeypatch.setattr(pruefen, "pruefe_pdf", lambda pdf, ausschluss=None, **kw: (ort.append(ausschluss) or
                        [Befund("text_ueber_text", "40", (1.0, 2.0, 3.0, 4.0), "50")]))
    monkeypatch.setattr(pruefen, "texte", lambda pdf: _sf_zeilen(_ideal_sp()))  # Schriftfeld, keine Rahmentexte
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    p = pruefe_lesbarkeit(pdf, "A3quer", REGELN)
    assert p["ok"] is None and _regeln_der(p) == {"Z-LES-1"} and "40" in p["maengel"][0]["text"] and ort[0]
    u = _bewerte(_ideal_sp(), plan_spannplatte_z(), _spec_sp(), pdf=pdf)
    assert u["bestanden"] is True and _pruefung(u, "lesbarkeit")["ok"] is None


def test_lesbarkeit_ohne_befund(monkeypatch, tmp_path):
    monkeypatch.setattr(pruefen, "pruefe_pdf", lambda pdf, ausschluss=None, **kw: [])
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    assert pruefe_lesbarkeit(pdf, "A3quer", REGELN)["ok"] is True


def test_durchmesser_tag_ist_zeichen():
    assert normtext("<MOD-DIAM>20 <MOD-EP>") == "Ø20 Ⓔ"
    plan = plan_buchse_z()
    ist = _ideal_bu()
    ist = replace(ist, masse=tuple(replace(m, praefix="<MOD-DIAM>") if m.art == "durchmesser" else m for m in ist.masse))
    assert pruefe_drehteil(ist, plan, REGELN)["ok"] is True
    assert _bewerte(ist, plan, _spec_bu())["bestanden"] is True
    ist = replace(ist, masse=tuple(replace(m, praefix="") if m.art == "durchmesser" else m for m in ist.masse))
    assert _regeln_der(pruefe_drehteil(ist, plan, REGELN)) == {"Z-DRE-1"}


# --- Jede Plan-Quelle wird ausgewertet -----------------------------------------------------------------------------------

def _quelle_modell():
    return plan_spannplatte_z(), _spec_sp(), _ideal_sp(), lambda m: m.name == "D1@f1_skizze"


@pytest.mark.parametrize("quelle", ["modell", "neu", "angabe", "rauheit", "form_lage", "bezug"])
def test_jede_quelle_wird_ausgewertet(quelle):
    if quelle == "neu":
        plan, spec, ist = plan_buchse_z(), _spec_bu(), _ideal_bu()
        ist = replace(ist, masse=tuple(m for m in ist.masse if not (m.art == "durchmesser" and m.wert == 50.0)))
    else:
        plan, spec, ist = plan_spannplatte_z(), _spec_sp(), _ideal_sp()
        if quelle == "modell":
            ist = replace(ist, masse=tuple(m for m in ist.masse if m.name != "D1@f1_skizze"))
        elif quelle == "angabe":
            ist = _ohne_notiz_mit(ist, "Ø8")
        else:
            ist = _ohne_angabe(ist, lambda a: a.art == quelle)
    assert any(m.quelle == quelle for m in plan)
    u = _bewerte(ist, plan, spec)
    assert u["bestanden"] is False, quelle


# --- Nachbesserung Review ---------------------------------------------------------------------------------------------------

_UEBERZAEHLIG = {
    "rauheit": (lambda mk: IstAngabe("rauheit", "haupt", "Ra 0,4", None, None, (), mk), "Z-TOL-4", "Ra 0,4"),
    "form_lage": (lambda mk: IstAngabe("form_lage", "haupt", "x", "<IGTOL-CIRC>", "0,01", (), mk), "Z-TOL-5", "0,01"),
    "bezug": (lambda mk: IstAngabe("bezug", "haupt", "C", None, None, ("C",), mk), "Z-TOL-6", "C"),
}


@pytest.mark.parametrize("art", list(_UEBERZAEHLIG))
def test_ueberzaehlige_angabe_mit_merkmal_ist_mangel(art):
    bau, regel_id, text = _UEBERZAEHLIG[art]
    ist = replace(_ideal_sp(), angaben=_ideal_sp().angaben + (bau("frei"),))
    u = _bewerte(ist, plan_spannplatte_z(), _spec_sp())
    assert u["bestanden"] is False
    m = next(m for m in u["maengel"] if m["regel"] == regel_id)
    assert m["text"].startswith("überzählig:") and text in m["text"] and "(frei)" in m["text"]


@pytest.mark.parametrize("art", list(_UEBERZAEHLIG))
def test_ueberzaehlige_angabe_ohne_merkmal_ist_mangel(art):
    """Review 4b (I2): ohne Merkmal ist eine überzählige Angabe nicht zuordenbar – harter Mangel der Art, keine
    bloße Meldung."""
    bau, regel_id, text = _UEBERZAEHLIG[art]
    ist = replace(_ideal_sp(), angaben=_ideal_sp().angaben + (bau(None),))
    u = _bewerte(ist, plan_spannplatte_z(), _spec_sp())
    assert u["bestanden"] is False
    m = next(m for m in u["maengel"] if m["regel"] == regel_id)
    assert m["text"].startswith("überzählig:") and "ohne Merkmal" in m["text"] and text in m["text"]
    assert m["merkmal"] == "ohne Merkmal"
    assert not any(x.startswith("überzählige") for x in u["meldungen"])


@pytest.mark.parametrize("text", ["ISO 2768 mK", "ISO 2768-m-K", "2768-2 K", "2768 – mK", "2768−mK", "2768-mk",
                                  "ISO 2768-1:1989 – mK", "ISO 2768-mK", "ISO 2768-1 mK", "2768 - mK"])
def test_iso_2768_k_treffer(text):
    assert _regeln_der(pruefe_sammelangaben(_notizen(_ideal_bu(), text), _spec_bu(), REGELN)) == {"Z-SAM-3"}


@pytest.mark.parametrize("text", ["ISO 2768-1:1989 – m", "ISO 2768-1 m Kanten ISO 13715", "2768-1 Kanten"])
def test_iso_2768_k_kein_treffer(text):
    assert _regeln_der(pruefe_sammelangaben(_notizen(_ideal_bu(), text), _spec_bu(), REGELN)) == set()


def test_sammelrauheit_wortgrenze():
    ist = _ohne_notiz_mit(_ideal_bu(), "Ra 3,2")
    assert "Z-SAM-7" not in _regeln_der(pruefe_sammelangaben(_notizen(ist, "Ra 3,2"), _spec_bu(), REGELN))
    assert "Z-SAM-7" in _regeln_der(pruefe_sammelangaben(_notizen(ist, "Ra 3,25"), _spec_bu(), REGELN))


def test_tolerenz_gleich_mit_rundungsrand():
    from swki.zeichnung.pruefen import _gleich

    assert _gleich(0.02, 0.0205) and not _gleich(0.02, 0.0206)


def test_nicht_geprueft_liste():
    u = _bewerte(_ideal_sp(), plan_spannplatte_z(), _spec_sp())
    assert set(u["nicht_geprueft"]) == {p["id"] for p in u["pruefungen"] if p["ok"] is None} >= {"schriftfeld", "lesbarkeit"}


def test_ausschluss_wie_zeichnen():
    from swki.zeichnung import zeichnen
    from swki.zeichnung.blatt import FORMATE

    for f in FORMATE:
        assert pruefen._ausschluss(f) == zeichnen._ausschluss(f)


# --- Gesamtreview: Schriftfeld auf dem Blatt (Controller „Z“) --------------------------------------------------------

def _sf_zeilen(ist, ohne=()):
    """PDF-Zeilen im Schriftfeld (A3quer: x 230–410, y 10–65 mm) mit den Werten der Pflichtfelder, ohne `ohne`."""
    sf = STANDARD["zeichnung"]["schriftfeld"]
    werte = [ist.eigenschaften.get(sf[f], "") for f in ("sachnummer", "titel", "ersteller", "ausgabedatum",
                                                         "dokumentart") if sf[f] not in ohne]
    return [("BENENNUNG:", (330.0, 44.5, 342.0, 47.0))] + [(w, (240.0 + 30 * i, 15.0, 260.0 + 30 * i, 18.0))
                                                         for i, w in enumerate(werte) if w]


def test_schriftfeld_pflichtfelder_auf_dem_blatt():
    ist = _ideal_sp()
    p = pruefe_schriftfeld(ist, STANDARD, REGELN, _sf_zeilen(ist))
    assert p["maengel"] == [] and p["ok"] is None and "Eigentümer" in p["hinweis"]


def test_schriftfeld_benennung_und_dokumentart_nicht_auf_dem_blatt():
    """Die Vorlage verknüpft BENENNUNG nicht mit der Eigenschaft: gesetzt, aber nicht auf dem Blatt → Z-SCH-1."""
    ist = _ideal_sp()
    p = pruefe_schriftfeld(ist, STANDARD, REGELN, _sf_zeilen(ist, ohne=("Benennung", "Dokumentart")))
    assert p["ok"] is False
    assert [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-SCH-1", "Benennung"), ("Z-SCH-1", "Dokumentart")]
    assert all("nicht auf dem Blatt" in m["text"] for m in p["maengel"])


def test_schriftfeld_ganzes_wort_und_mehrfachmenge():
    """„Spannplatte“ steckt in „SpannplatteZ“ – das zählt nicht; zwei gleiche Werte brauchen zwei Zeilen."""
    ist = _mit_eig(_ideal_sp(), Benennung="Spannplatte", Zeichnungsnummer="SpannplatteZ")
    zeilen = [z for z in _sf_zeilen(ist) if z[0] != "Spannplatte"]
    p = pruefe_schriftfeld(ist, STANDARD, REGELN, zeilen)
    assert [m["merkmal"] for m in p["maengel"]] == ["Benennung"]
    gleich = _mit_eig(_ideal_sp(), Benennung="Spannplatte", Zeichnungsnummer="Spannplatte")
    einmal = [z for z in _sf_zeilen(gleich)]
    einmal.remove(next(z for z in einmal if z[0] == "Spannplatte"))
    assert [m["merkmal"] for m in pruefe_schriftfeld(gleich, STANDARD, REGELN, einmal)["maengel"]] == ["Benennung"]


def test_schriftfeld_wert_ausserhalb_des_schriftfelds_zaehlt_nicht():
    ist = _ideal_sp()
    zeilen = _sf_zeilen(ist, ohne=("Benennung",)) + [(ist.eigenschaften["Benennung"], (50.0, 200.0, 70.0, 203.0))]
    assert [m["merkmal"] for m in pruefe_schriftfeld(ist, STANDARD, REGELN, zeilen)["maengel"]] == ["Benennung"]


def test_schriftfeld_ohne_pdf_nicht_geprueft():
    p = pruefe_schriftfeld(_ideal_sp(), STANDARD, REGELN)
    assert p["ok"] is None and "kein PDF" in p["hinweis"]


def test_bewerte_prueft_schriftfeld_am_pdf(monkeypatch, tmp_path):
    ist = _ideal_sp()
    monkeypatch.setattr(pruefen, "pruefe_pdf", lambda pdf, ausschluss=None, **kw: [])
    monkeypatch.setattr(pruefen, "texte", lambda pdf: _sf_zeilen(ist, ohne=("Benennung",)))
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    u = _bewerte(ist, plan_spannplatte_z(), _spec_sp(), pdf=pdf)
    assert u["bestanden"] is False
    assert [(m["regel"], m["merkmal"]) for m in u["maengel"] if m["pruefung"] == "schriftfeld"] == [("Z-SCH-1", "Benennung")]


# --- Gesamtreview (c): Lage der Sammelangaben -------------------------------------------------------------------------

def _verschiebe_notiz(ist, teil, lage):
    return replace(ist, angaben=tuple(replace(a, lage=lage) if a.art == "hinweis" and teil in a.text else a
                                      for a in ist.angaben))


def test_sammelangaben_ideal_im_band():
    assert pruefe_sammelangaben(_ideal_sp(), _spec_sp(), REGELN)["ok"] is True


def test_sammelangabe_unter_dem_blatt_ist_z_sam_1():
    p = pruefe_sammelangaben(_verschiebe_notiz(_ideal_sp(), "Allgemeintoleranzen", (230.0, -50.0)), _spec_sp(), REGELN)
    assert p["ok"] is False and [(m["regel"], m["merkmal"]) for m in p["maengel"]] == [("Z-SAM-1", "sammelangabe")]
    assert "außerhalb" in p["maengel"][0]["text"]


def test_sammelrauheit_weg_vom_schriftfeld_ist_z_sam_7():
    p = pruefe_sammelangaben(_verschiebe_notiz(_ideal_sp(), "Ra 3,2", (60.0, 250.0)), _spec_sp(), REGELN)
    assert p["ok"] is False and _regeln_der(p) == {"Z-SAM-7"}


def test_sammelangabe_ohne_lage_nicht_geprueft():
    p = pruefe_sammelangaben(_verschiebe_notiz(_ideal_sp(), "Allgemeintoleranzen", None), _spec_sp(), REGELN)
    assert p["ok"] is None and "Lage" in p["hinweis"]


def test_halbzeug_als_eigene_notiz_ist_z_sam_5():
    """Die Regel einer Notiz folgt ihrer ersten Zeile aus `sammelangaben`: eine einzelne Halbzeug-Notiz ist Z-SAM-5."""
    ist = _notizen(_ideal_sp(), "Halbzeug: Flach EN 10058 – 120 × 20")
    ist = replace(ist, angaben=ist.angaben[:-1] + (replace(ist.angaben[-1], lage=(50.0, 50.0)),))
    assert _regeln_der(pruefe_sammelangaben(ist, _spec_sp(), REGELN)) == {"Z-SAM-5"}
