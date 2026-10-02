"""Fehlercodes der Normteile (Spec 3a §8)."""

from swki.cli import SwkiFehler

NORMTEIL_UNBEKANNT = "NORMTEIL_UNBEKANNT"
NORMLAENGE_UNGUELTIG = "NORMLAENGE_UNGUELTIG"
NORMVARIANTE_UNBEKANNT = "NORMVARIANTE_UNBEKANNT"
NORMTEIL_GESPERRT = "NORMTEIL_GESPERRT"
NORMTABELLE_UNGUELTIG = "NORMTABELLE_UNGUELTIG"
NORMVORLAGE_UNGEPRUEFT = "NORMVORLAGE_UNGEPRUEFT"
NORMTEIL_PRUEFUNG = "NORMTEIL_PRUEFUNG"


class NormteilFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}
