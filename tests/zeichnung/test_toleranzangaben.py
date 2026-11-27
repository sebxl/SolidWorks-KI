"""Zeichnungsableitung Z1.3 Stufe 4 Task 1: Texte und Werte der Anforderungen."""

from pathlib import Path

import yaml

from swki.zeichnung.toleranzangaben import (FormLage, Toleranz, behandlungstext, form_lage_angaben, halbzeugtext,
                                            rauheitstext, sammelangaben, toleranz_aus, toleranztext)

REF = Path(__file__).parents[1] / "referenz"


def _lade(pfad: str) -> dict:
    return yaml.safe_load((REF / pfad).read_text(encoding="utf-8"))


def test_toleranztext():
    assert toleranztext(Toleranz("H7", None, None, True)) == "H7 Ⓔ"
    assert toleranztext(Toleranz(None, 0.02, -0.02, False)) == "±0,02"
    assert toleranztext(Toleranz(None, 0.1, -0.05, False)) == "+0,1/−0,05"
    assert toleranz_aus(None, None, False) is None


def test_toleranz_aus():
    assert toleranz_aus("H7", None, False) == Toleranz("H7", None, None, False)
    assert toleranz_aus(None, {"oben": 0.1, "unten": -0.05}, True) == Toleranz(None, 0.1, -0.05, True)


def test_rauheit_und_formlage():
    assert rauheitstext({"Ra": 0.8}) == "Ra 0,8" and rauheitstext({"Rz": 6.3}) == "Rz 6,3"
    fl, meld = form_lage_angaben("t1", [{"art": "parallelitaet", "wert": 0.05, "bezug": ["A"]}])
    assert fl == [FormLage("t1", "parallelitaet", "<IGTOL-PARA>", "0,05", ("A",), False)] and meld == []


def test_formlage_it_ohne_tabelle():
    fl, meld = form_lage_angaben("f1", [{"art": "rundheit", "it": 4}])
    assert fl == [] and meld == ["FORM_LAGE_IT_OHNE_TABELLE: f1 rundheit IT4 – keine ISO-286-Tabelle"]


def test_behandlung_iso15787():
    b = {"art": "einsatzhaerten", "haerte": {"wert": 60, "plus": 2, "minus": 2, "verfahren": "HRC"},
         "tiefe": {"art": "CHD", "wert": 0.8, "plus": 0.4, "minus": 0, "grenzhaerte": "550 HV1"}, "zustand": "fertigteil"}
    assert behandlungstext(b) == "einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm (550 HV1)"
    assert behandlungstext({"art": "bruenieren"}) == "brüniert"


def test_behandlung_varianten():
    assert behandlungstext({"art": "haerten", "haerte": {"wert": 58, "verfahren": "HRC"}}) == "gehärtet ≥ 58 HRC"
    assert behandlungstext({"art": "haerten", "haerte": {"wert": 58, "plus": 2, "minus": 1, "verfahren": "HRC"}}) \
        == "gehärtet (58 +2/−1) HRC"
    assert behandlungstext({"art": "nitrieren", "zustand": "vor_schleifen"}) == "nitriert (vor dem Schleifen)"
    assert behandlungstext({"art": "verzinken", "schicht": {"norm": "ISO 2081", "bezeichnung": "Fe//Zn8"}}) \
        == "verzinkt, ISO 2081 Fe//Zn8"


def test_halbzeug():
    assert halbzeugtext({"art": "flach", "norm": "EN 10058", "masse": "120 x 20"}) == "Halbzeug: Flach EN 10058 – 120 × 20"
    assert halbzeugtext({"art": "rund", "norm": "EN 10060", "masse": "55", "toleranz": "h11", "zustand": "blank"}) \
        == "Halbzeug: Rund EN 10060 – 55, h11, blank"


def test_sammelangaben_reihenfolge():
    spec = _lade("zeichnung/buchse_z.yaml")
    assert sammelangaben(spec) == [
        "Allgemeintoleranzen ISO 2768-1:1989 – m", "Tolerierung ISO 8015:2011", "Kanten ISO 13715 −0,1 … −0,3",
        "Maßgebend ist die Zeichnung",
        "einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm (550 HV1)",
        "Halbzeug: Rund EN 10060 – 55"]
    assert sammelangaben(_lade("stil/spannplatte.yaml"))[:4] == sammelangaben(spec)[:4]


def test_toleranz_aus_ausdruck():
    assert toleranz_aus(None, {"oben": "=T/2", "unten": "=-T/2"}, False, {"T": 0.04}) == Toleranz(None, 0.02, -0.02, False)
