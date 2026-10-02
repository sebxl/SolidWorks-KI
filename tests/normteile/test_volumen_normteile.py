"""Sollvolumen (volumen: auto) gegen eine unabhängige Handrechnung aus Zylindern, Prismen und 45°-Fasenringen."""

import math

import pytest

from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle
from swki.pruefung.geometrie import volumen_auto


def _volumen(norm, groesse, laenge=None):
    t = lade_normtabelle(norm)
    spec = erzeuge_spec(t, Anfrage(t["norm"], groesse, laenge, t["vorgabe_variante"]), vorlage_text(t))
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch"
    return volumen, t["groessen"][groesse]["masse"]


def fasenring(r_schwerpunkt: float, a: float) -> float:
    """45°-Fase als Ring: rechtwinkliges Dreieck mit Kathete a, Schwerpunkt im Abstand r von der Achse (Pappus)."""
    return 2 * math.pi * r_schwerpunkt * a * a / 2


def sechskant(s: float) -> float:
    """Fläche eines regelmäßigen Sechsecks mit Schlüsselweite s."""
    return 3**0.5 / 2 * s**2


@pytest.mark.parametrize(("groesse", "laenge"), [("M5", 8), ("M10", 40), ("M16", 160)])
def test_iso4762(groesse, laenge):
    v, m = _volumen("ISO 4762", groesse, laenge)
    d, dk, k, s, t, p = (m[x] for x in ("d", "dk", "k", "s", "t", "p"))
    a = k / 10
    kopf = math.pi * (dk / 2) ** 2 * k - fasenring(dk / 2 - a / 3, a)
    schaft = math.pi * (d / 2) ** 2 * laenge - fasenring(d / 2 - p / 3, p)
    assert v == pytest.approx(kopf + schaft - sechskant(s) * t, rel=1e-9)
