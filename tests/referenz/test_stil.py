"""Referenz Paket Konstruktionsstil (ohne SolidWorks): die Spannplatte im neuen Stil gibt keine Stilhinweise, dieselbe
Platte nach den alten Regeln (vorher/) genau die erwarteten."""

from pathlib import Path

from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

STIL = Path(__file__).parent / "stil"


def test_spannplatte_ohne_hinweise():
    assert hinweise(lade_spec(STIL / "spannplatte.yaml")) == []


def test_vorher_meldet_spiegeln_muster_und_fasen():
    gemeldet = [(h["art"], h["pfad"]) for h in hinweise(lade_spec(STIL / "vorher" / "spannplatte.yaml"))]
    assert ("zusammenfassen", "features[1]") in gemeldet          # zwei spiegelbildliche Taschen in einer Skizze
    assert ("zusammenfassen", "features[2]") in gemeldet          # Lochreihe 5 × M6
    assert ("fertigung", "features[2]") in gemeldet and ("fertigung", "features[3]") in gemeldet
