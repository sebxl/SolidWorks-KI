"""Nachträge zum Rückleser (Plan Z1.4 Task 4b) in den reinen Prüfungen: Meldungscode → Regel (`MELDUNG_REGEL`),
Merkmal je Angabe über die angehängte Kante, Instanzzahl über dem Rahmen, Zeichnungsmaße, Rahmen für die Lesbarkeit."""

import re
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from swki.zeichnung import pruefen
from swki.zeichnung.ist import IstAngabe
from swki.zeichnung.pruefen import (MELDUNG_REGEL, NUR_BERICHT, bewerte, masse_umbenennen, meldungscode,
                                    merkmale_zuordnen, normtext, pruefe_lesbarkeit, pruefe_toleranzen, soll_luecken)
from swki.zeichnung.regeln import lade_regeln, regel
from tests.zeichnung.ist_bau import ideal_ist, plan_buchse_z, plan_spannplatte_z
from tests.zeichnung.test_massplan import _lade_ref

REGELN = lade_regeln()
STANDARD = yaml.safe_load((Path(__file__).parents[2] / "config" / "standard.yaml").read_text(encoding="utf-8"))
ZEICHNUNG = Path(__file__).parents[2] / "swki" / "zeichnung"


def _spec_sp():
    return _lade_ref("zeichnung/spannplatte_z.yaml")


def _ideal_sp():
    return ideal_ist(plan_spannplatte_z(), spec=_spec_sp())


def _bewerte(ist, plan=None, spec=None, **kw):
    return bewerte(ist, plan or plan_spannplatte_z(), spec or _spec_sp(), STANDARD, REGELN, **kw)


def _pruefung(urteil: dict, id_: str) -> dict:
    return next(p for p in urteil["pruefungen"] if p["id"] == id_)


# --- Meldungscode → Regel ---------------------------------------------------------------------------------------------

def _codes_im_code() -> set[str]:
    """Alle Meldungscodes in swki/zeichnung/*.py: `"CODE: …` (auch in f-Strings) und Codes, die als Name in einem Tupel
    stehen und erst per f"{code}: …" Meldung werden (`anmerkungen_pruefen`: ANMERKUNG_KREUZT, ANMERKUNG_ZU_NAH)."""
    codes = set()
    for p in ZEICHNUNG.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        codes |= set(re.findall(r'"([A-Z][A-Z_]+):', text))
        codes |= set(re.findall(r'\(\("([A-Z][A-Z_]+)",', text)) | set(re.findall(r'\("([A-Z][A-Z_]+)", \[', text))
    return codes


def test_jeder_meldungscode_hat_regel():
    codes = _codes_im_code()
    assert {"ANMERKUNG_KREUZT", "ANMERKUNG_ZU_NAH", "RAUHEIT_NUR_EINE_INSTANZ", "SCHNITT_BUCHSTABE"} <= codes
    ohne = sorted(c for c in codes if c not in MELDUNG_REGEL and c not in NUR_BERICHT)
    assert ohne == [], f"Meldungscodes ohne Regel und ohne Eintrag „nur Bericht“: {ohne}"
    assert not set(MELDUNG_REGEL) & set(NUR_BERICHT)
    for code, (pruefung, regel_id) in MELDUNG_REGEL.items():
        assert regel(REGELN, regel_id).pruefung == pruefung, code
    assert all(grund.strip() for grund in NUR_BERICHT.values())


def test_tabelle_wie_nachtrag():
    """Plan Task 4b, Nachtrag 2: die genannten Zuordnungen."""
    erwartet = {"ANMERKUNG_KREUZT": "Z-LES-1", "ANGABE_ZU_NAH": "Z-LES-1", "ANSATZ_NICHT_FREI": "Z-LES-1",
                "LESBARKEIT": "Z-LES-1", "ANMERKUNG_ZU_NAH": "Z-LES-1", "SCHRAFFUR_UNGELESEN": "Z-LES-1",
                "EINZELHEIT_BUCHSTABE": "Z-ANS-2", "SCHNITT_BUCHSTABE": "Z-ANS-2",
                "RAUHEIT_NICHT_GESETZT": "Z-TOL-4", "FORM_LAGE_NICHT_GESETZT": "Z-TOL-5",
                "TOLERANZ_NICHT_GESETZT": "Z-TOL-1", "BEZUG_NICHT_GESETZT": "Z-TOL-6",
                "RAUHEIT_NUR_EINE_INSTANZ": "Z-TOL-4", "FORM_LAGE_NUR_EINE_INSTANZ": "Z-TOL-5",
                "MASS_NICHT_DAUERHAFT": "Z-VOLL-1", "MASS_NICHT_GEPLANT": "Z-VOLL-1",
                "TOLERANZ_OHNE_MASS": "Z-TOL-1", "TOLERANZ_MEHRDEUTIG": "Z-TOL-1"}
    assert {c: MELDUNG_REGEL[c][1] for c in erwartet} == erwartet
    assert "FUNKTION_UNBESTAETIGT" in NUR_BERICHT


def test_meldungscode():
    assert meldungscode("ANMERKUNG_KREUZT: st rauheit „Ra 0,8“ – Kante (1)") == "ANMERKUNG_KREUZT"
    assert meldungscode("irgendein Text") is None


def test_unbekannte_meldung_ist_mangel():
    for meldung in ("NEU_ERFUNDEN: f1 – etwas", "Text ohne Code"):
        u = _bewerte(_ideal_sp(), meldungen=[meldung])
        assert u["bestanden"] is False
        m = next(m for m in u["maengel"] if meldung in m["text"])
        assert m["regel"] == "Z-VOLL-1" and "unbekannte Zeichnungsmeldung" in m["text"]


@pytest.mark.parametrize("meldung,pruefung,regel_id", [
    ("RAUHEIT_NUR_EINE_INSTANZ: st Ra 0,8 – Symbol an einer von 2 Instanzen", "toleranzen", "Z-TOL-4"),
    ("FORM_LAGE_NUR_EINE_INSTANZ: t1 parallelitaet 0,05 – „2 ד über dem Rahmen nicht gesetzt", "toleranzen", "Z-TOL-5"),
    ("MASS_NICHT_DAUERHAFT: D3@m1 – keine sichtbare Kante; Toleranz und Zusatz entfallen", "vollstaendig", "Z-VOLL-1"),
    ("SCHNITT_BUCHSTABE: „C“ verlangt, Schnitt trägt „A“", "ansichten", "Z-ANS-2"),
    ("EINZELHEIT_BUCHSTABE: „Z“ verlangt, Einzelheitenkreis trägt keinen", "ansichten", "Z-ANS-2"),
    ("BEZUG_NICHT_GESETZT: B – Buchstabe nicht gesetzt", "toleranzen", "Z-TOL-6"),
])
def test_zeichnungsmeldung_wird_mangel(meldung, pruefung, regel_id):
    u = _bewerte(_ideal_sp(), meldungen=[meldung])
    assert u["bestanden"] is False and _pruefung(u, pruefung)["ok"] is False
    assert any(m["regel"] == regel_id and m["pruefung"] == pruefung and m["text"] == meldung for m in u["maengel"])


def test_anmerkung_kreuzt_ist_hinweis():
    meldung = "ANMERKUNG_KREUZT: st rauheit „Ra 0,8“ – Rechteck auf Linie (1), Maßlinie (2), Kante (1)"
    u = _bewerte(_ideal_sp(), meldungen=[meldung])
    assert u["bestanden"] is True
    p = _pruefung(u, "lesbarkeit")
    assert p["ok"] is None and [m["merkmal"] for m in p["maengel"] if m["text"] == meldung] == ["st"]
    assert "lesbarkeit" in u["nicht_geprueft"]


def test_nur_bericht_bleibt_meldung():
    meldung = "LAUF_NICHT_BESTANDEN: Lauf 1 ist nicht bestanden – Zeichnung nur zur Ansicht"
    u = _bewerte(_ideal_sp(), meldungen=[meldung])
    assert u["bestanden"] is True and meldung in u["meldungen"]
    assert not any(meldung in m["text"] for m in u["maengel"])


def test_meldung_doppelt_ein_mangel():
    """Die Übergabe enthält die Meldungen des Maßplans schon; `zeichnung_pruefen` rechnet sie neu (Advisor 28.11.)."""
    meldung = "TOLERANZ_OHNE_MASS: f1"
    u = _bewerte(_ideal_sp(), meldungen=[meldung, meldung], meldungen_soll=[meldung])
    assert sum(1 for m in u["maengel"] if m["text"] == meldung) == 1
    assert soll_luecken([meldung, meldung]) == soll_luecken([meldung])


def test_meldungen_des_ruecklesers():
    ist = replace(_ideal_sp(), meldungen=("RUECKLESEN_UNVOLLSTAENDIG: Zeichenansicht1 – Maß RD3 ohne Wert",))
    u = _bewerte(ist)
    assert u["bestanden"] is False
    assert any(m["regel"] == "Z-VOLL-1" and "RD3" in m["text"] for m in u["maengel"])


# --- Form/Lage: Instanzen über dem Rahmen ---------------------------------------------------------------------------

def test_ideal_traegt_anzahl():
    ist = _ideal_sp()
    t1 = next(a for a in ist.angaben if a.art == "form_lage" and a.merkmal == "t1")
    f1 = next(a for a in ist.angaben if a.art == "form_lage" and a.merkmal == "f1")
    assert t1.anzahl == 2 and f1.anzahl is None   # zwei Taschen (s1 spiegelt t1), eine Unterseite
    assert _bewerte(ist)["bestanden"] is True


def test_form_lage_anzahl_fehlt():
    ist = _ideal_sp()
    angaben = tuple(replace(a, anzahl=None) if a.art == "form_lage" and a.merkmal == "t1" else a for a in ist.angaben)
    u = _bewerte(replace(ist, angaben=angaben))
    m = [m for m in u["maengel"] if m["regel"] == "Z-TOL-5"]
    assert u["bestanden"] is False and len(m) == 1 and "2 ×" in m[0]["text"] and m[0]["merkmal"] == "t1"


def test_form_lage_anzahl_ohne_soll_nicht_geprueft():
    """Direktaufruf ohne `anzahl` (Task 3): die Instanzzahl wird nicht verglichen."""
    ist = _ideal_sp()
    angaben = tuple(replace(a, anzahl=None) for a in ist.angaben)
    assert pruefe_toleranzen(replace(ist, angaben=angaben), plan_spannplatte_z(), REGELN)["ok"] is True


def test_mmc_tag():
    assert normtext("0,02 <MOD-MMC>") == "0,02 Ⓜ"


# --- Merkmal je Angabe über die angehängte Kante -------------------------------------------------------------------

def _ohne_merkmal(ist):
    return replace(ist, angaben=tuple(replace(a, merkmal=None) for a in ist.angaben))


def _angabe(art, text, features, symbol=None, wert=None, bezug=()):
    return IstAngabe(art, "v", text, symbol, wert, tuple(bezug), None, None, tuple(features))


def test_merkmal_ueber_spiegel_und_unterfeature():
    spec, plan = _spec_sp(), plan_spannplatte_z()
    ist = replace(_ideal_sp(), angaben=(
        _angabe("rauheit", "Ra 1,6", ("Schnitt1", "s1")),          # gespiegelter Taschenboden → t1
        _angabe("rauheit", "Ra 0,8", ("st", "st_fase")),            # Stiftbohrung samt Fase → st
        _angabe("hinweis", "5 × M6 – 10 tief\r\nSenkung Ø6 × 90°", ("f1", "m1")),  # Muster der Gewinde → g1
        _angabe("hinweis", "2 × Ø8 H7 <MOD-EP>\r\n15 tief\r\nFase 0,5 × 45°", ("f1", "st_fase")),  # f1 ohne Angabe
        _angabe("bezug", "A", ("Schnitt1", "f1"), bezug=("A",)),
        _angabe("form_lage", "<IGTOL-PARA> 0,05", ("Schnitt1", "t1"), "<IGTOL-PARA>", "0,05", ("A",)),
    ))
    aus = merkmale_zuordnen(ist, spec, plan)
    assert [a.merkmal for a in aus.angaben] == ["t1", "st", "g1", "st", "f1", "t1"]


def test_merkmal_mehrdeutig_nach_inhalt():
    """Kante zwischen zwei Merkmalen mit Rauheit im Plan: der Inhalt entscheidet; gleicher Inhalt → kein Merkmal."""
    spec, plan = _spec_sp(), plan_spannplatte_z()
    ist = replace(_ideal_sp(), angaben=(_angabe("rauheit", "Ra 0,8", ("st", "t1")),
                                        _angabe("rauheit", "Ra 3,2", ("st", "t1"))))
    assert [a.merkmal for a in merkmale_zuordnen(ist, spec, plan).angaben] == ["st", None]


def test_merkmal_ausserhalb_des_plans():
    """An einer Fläche ohne Eintrag dieser Art: das Merkmal der Kante (mehrere mit „/“) – überzählig, ein harter
    Mangel; ohne Feature-Namen bleibt es None (nur Meldung)."""
    spec, plan = _spec_sp(), plan_spannplatte_z()
    ist = replace(_ideal_sp(), angaben=(_angabe("rauheit", "Ra 1,6", ("Schnitt1", "f1")),
                                        _angabe("rauheit", "Ra 1,6", ("g1", "f1")),
                                        _angabe("rauheit", "Ra 1,6", ("Schnitt1",)),
                                        _angabe("rauheit", "Ra 1,6", ())))
    assert [a.merkmal for a in merkmale_zuordnen(ist, spec, plan).angaben] == ["f1", "f1/g1", None, None]


def test_merkmal_bleibt_wenn_gesetzt():
    ist = _ideal_sp()
    assert merkmale_zuordnen(ist, _spec_sp(), plan_spannplatte_z()) == ist


def test_zugeordnete_angaben_bestehen():
    """Ideal ohne Merkmale, aber mit den Feature-Namen wie live gelesen → nach der Zuordnung bestanden."""
    spec, plan = _spec_sp(), plan_spannplatte_z()
    features = {"t1": ("Schnitt1", "s1"), "st": ("st", "st_fase"), "f1": ("Schnitt1", "f1")}
    ist = _ideal_sp()
    ist = replace(ist, angaben=tuple(replace(a, merkmal=None, features=features.get(a.merkmal, ()))
                                     for a in ist.angaben))
    assert _bewerte(merkmale_zuordnen(ist, spec, plan))["bestanden"] is True


# --- Zeichnungsmaße ---------------------------------------------------------------------------------------------------

def test_masse_umbenennen():
    ist = _ideal_sp()
    m = next(m for m in ist.masse if m.name == "D3@m1")
    ist = replace(ist, masse=tuple(replace(x, name="RD1@Zeichenansicht1") if x is m else x for x in ist.masse))
    aus = masse_umbenennen(ist, {"D3@m1": "RD1@Zeichenansicht1", "D1@x": "RD7@Zeichenansicht2"})
    assert sum(1 for x in aus.masse if x.name == "D3@m1") == 1
    assert not any(x.name.startswith("RD") for x in aus.masse)
    assert masse_umbenennen(ist, None) == ist


# --- Lesbarkeit mit gelegten Rahmen --------------------------------------------------------------------------------

def test_lesbarkeit_bekommt_rahmen(monkeypatch, tmp_path):
    gesehen = {}
    monkeypatch.setattr(pruefen, "pruefe_pdf", lambda pdf, ausschluss=None, **kw: gesehen.update(kw) or [])
    monkeypatch.setattr(pruefen, "texte", lambda pdf: [("0,05 A", (1.0, 2.0, 3.0, 4.0)), ("0,02", (5.0, 6.0, 7.0, 8.0)),
                                                       ("40,00", (9.0, 9.0, 10.0, 10.0))])
    pdf = tmp_path / "z.pdf"
    pdf.write_bytes(b"%PDF")
    p = pruefe_lesbarkeit(pdf, "A3quer", REGELN, rahmen_texte=("0,05 A", "0,02"))
    assert p["ok"] is True
    assert gesehen["rahmen"] == (("0,05 A", (1.0, 2.0, 3.0, 4.0)), ("0,02", (5.0, 6.0, 7.0, 8.0)))
    gesehen.clear()
    _bewerte(_ideal_sp(), pdf=pdf)
    assert {t for t, _ in gesehen["rahmen"]} == {"0,05 A", "0,02"}


def test_rahmen_texte_aus_ist():
    texte = pruefen.rahmen_texte(_ideal_sp())
    assert sorted(texte) == ["0,02", "0,05 A"]
    mmc = IstAngabe("form_lage", "v", "x", "<IGTOL-POSI>", "0,1 <MOD-MMC>", ("A", "B"))
    assert pruefen.rahmen_texte(replace(_ideal_sp(), angaben=(mmc,))) == ("0,1 A B",)


def test_buchse_ideal_bleibt_bestanden():
    spec = _lade_ref("zeichnung/buchse_z.yaml")
    assert bewerte(ideal_ist(plan_buchse_z(), spec=spec), plan_buchse_z(), spec, STANDARD, REGELN)["bestanden"] is True
