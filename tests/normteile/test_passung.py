"""Normteile passen zu den Normbohrungen aus Stufe 2c (swki/wissen/bohrungsnormen.yaml)."""

from swki.normteile.tabelle import lade_normtabelle
from swki.spec.normen import normmasse


def test_zylinderschraube_passt_in_ihre_normbohrung():
    t = lade_normtabelle("ISO 4762")
    gemeinsam = [g for g in t["groessen"] if normmasse("zylinderschraube", g)]
    assert len(gemeinsam) >= 4
    for g in gemeinsam:
        m, b = t["groessen"][g]["masse"], normmasse("zylinderschraube", g)
        assert m["d"] < b["durchgang"] and m["dk"] < b["senkung_d"] and m["k"] <= b["senkung_t"], g


def test_stift_passt_in_sein_stiftloch():
    t = lade_normtabelle("ISO 8734")
    gemeinsam = [g for g in t["groessen"] if normmasse("stift", g)]
    assert len(gemeinsam) >= 4
    for g in gemeinsam:
        assert t["groessen"][g]["masse"]["d"] == normmasse("stift", g)["durchmesser"], g
