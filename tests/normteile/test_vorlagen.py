"""Jede Normtabelle ist ohne Befund; jede Vorlage hat genau die Parameter ihrer Tabelle (plus l) und ist selbst gültig;
jede Größe und Länge ergibt eine gültige Spezifikation ohne feste Zahlen (Spec 3a §11)."""

import pytest
import yaml

from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle, normen, tabellen_befunde

NORMEN = normen()


def test_es_gibt_normtabellen():
    assert NORMEN


@pytest.mark.parametrize("norm", NORMEN)
def test_tabelle_ohne_befund(norm):
    assert tabellen_befunde(lade_normtabelle(norm)) == []


@pytest.mark.parametrize("norm", NORMEN)
def test_vorlage_passt_zur_tabelle(norm):
    t = lade_normtabelle(norm)
    vorlage = yaml.safe_load(vorlage_text(t))
    assert set(vorlage["parameter"]) == set(t["parameter"]) | ({"l"} if t["laenge"] else set())
    assert spec_befunde(vorlage) == []


@pytest.mark.parametrize("norm", NORMEN)
def test_jede_groesse_und_laenge_ergibt_gueltige_spec(norm):
    t = lade_normtabelle(norm)
    text = vorlage_text(t)
    fehler = {}
    for g, z in t["groessen"].items():
        for laenge in z.get("laengen") or [None]:
            a = Anfrage(t["norm"], g, None if laenge is None else float(laenge), t["vorgabe_variante"])
            if befunde := spec_befunde(erzeuge_spec(t, a, text)):
                fehler[a.schluessel] = befunde
    assert fehler == {}
